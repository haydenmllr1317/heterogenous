"""Definitions of node types.

This module provides definitions for various types of quantum network nodes.
All node types inherit from the base Node type, which inherits from Entity.
Node types can be used to collect all the necessary hardware and software for a network usage scenario.
"""
import sys
from math import inf
from typing import TYPE_CHECKING, Any, List, Union

import numpy as np

if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline
    from sequence.message import Message
    from sequence.protocol import StackProtocol
    from sequence.resource_management.memory_manager import MemoryInfo
    from sequence.network_management.reservation import Reservation
    from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
    # from qchannels import QuantumChannel
    from memory import Memory
    from photon import Photon
    from sequence.app.request_app import RequestApp

from sequence.kernel.entity import Entity, ClassicalEntity
from memory import MemoryArray
from time_bin_bsm import BSM, HetTimeBinBSM
from sequence.components.light_source import LightSource
from detector import Detector
from sequence.qkd.BB84 import BB84
from sequence.qkd.cascade import Cascade
from sequence.resource_management.resource_manager import ResourceManager
from network_manager import NewNetworkManager, NetworkManager
from encoding import *
from sequence.utils import log
from sequence.components.bsm import SingleAtomBSM, SingleHeraldedBSM, PolarizationBSM
from encoding import time_bin, yb_time_bin
from copy import copy
from generation import YbEGB
from sequence.topology.node import Node
from qfc import QFC

## THIS IS MEANT TO BE A REPLACEMENT NOT AND INHERITANCE OF BSMNode
# TODO CHANGE THE __init__() to better match BSMNode (use component templates instead of encoding type)
class HetBSMNode(Node):
    """Bell state measurement node.

    This node provides bell state measurement and the EntanglementGenerationB protocol for entanglement generation.
    Creates a SingleAtomBSM object within local components.

    Attributes:
        name (str): label for node instance.
        timeline (Timeline): timeline for simulation.
        eg (EntanglementGenerationB): entanglement generation protocol instance.
    """
    # NOTE: CHANGING THIS
    def __init__(self, name: str, timeline: "Timeline", other_nodes: List[str],
                 seed=None, component_templates=None) -> None:
        """Constructor for BSM node.

        Args:
            name (str): name of node.
            timeline (Timeline): simulation timeline.
            other_nodes (List[str]): 2-member list of node names for adjacent quantum routers.
        """

        super().__init__(name, timeline, seed)
        if not component_templates:
            component_templates = {}

        self.encoding_type = component_templates.get('encoding_type', 'single_atom')

        # create BSM object with optional args
        bsm_name = name + ".BSM"
        if self.encoding_type == 'single_atom':
            bsm_args = component_templates.get("SingleAtomBSM", {})
            bsm = SingleAtomBSM(bsm_name, timeline, **bsm_args)
        elif self.encoding_type == 'single_heralded':
            bsm_args = component_templates.get("SingleHeraldedBSM", {})
            bsm = SingleHeraldedBSM(bsm_name, timeline, **bsm_args)
        elif self.encoding_type == 'het_time_bin':
            bsm_args = component_templates.get("Het_TimeBinBSM", {})
            bsm = HetTimeBinBSM(bsm_name, timeline, **bsm_args)
        else:
            raise ValueError(f'Encoding type {self.encoding_type} not supported')
        
        # add QFCs
        qfc0 = QFC(name+'.QFC0', self.timeline)
        qfc1 = QFC(name+'.QFC1', self.timeline)
        qfc0.add_receiver(bsm)
        qfc1.add_receiver(bsm)
        self.add_component(qfc0)
        self.add_component(qfc1)

        self.add_component(bsm)
        self.set_first_component(bsm_name)

        self.qfc_noise_counter = 0
        self.conversion_counter = 0
        self.noise_to_detector = 0
        self.detectors_got = 0
        self.detectors_recorded = 0
        self.trigger_sent = 0

        # TODO if YbEGB inherits from EGB than we need to have multiple options
        self.eg = YbEGB(self, "{}_eg".format(name), other_nodes)
        bsm.attach(self.eg)

    # overwrote this method so that photons go straight to correct QFCs
    def receive_qubit(self, src: str, photon) -> None:
        index = src.find('_')
        self.components[self.name+'.QFC'+src[index+1:]].get(photon)
    
    # TODO figure out if this is duplicitous and an unecesssary change from the Node version
    def receive_message(self, src: str, msg: "Message") -> None:
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if protocol.protocol_type == msg.protocol_type or type(protocol) == msg.protocol_type:
                if protocol.received_message(src, msg):
                    return

        # if we reach here, we didn't successfully receive the message in any protocol
        print(src, msg)
        raise Exception("Unknown protocol")

    def eg_add_others(self, other):
        """Method to add other protocols to entanglement generation protocol.

        Local entanglement generation protocol stores name of other protocol for communication.
        NOTE: entanglement generation protocol should be first protocol in protocol list.

        Args:
            other (EntanglementProtocol): other entanglement protocol instance.
        """

        self.protocols[0].others.append(other.name)


class HetQR(Node):
    """Node for entanglement distribution networks.

    This node type comes pre-equipped with memory hardware, along with the default SeQUeNCe modules (sans application).
    By default, a quantum memory array is included in the components of this node.

    Attributes:
        resource_manager (ResourceManager): resource management module.
        network_manager (NetworkManager): network management module.
        map_to_middle_node (Dict[str, str]): mapping of router names to intermediate bsm node names.
        app (any): application in use on node.
        gate_fid (float): fidelity of multi-qubit gates (usually CNOT) that can be performed on the node.
        meas_fid (float): fidelity of single-qubit measurements (usually Z measurement) that can be performed on the node.
    """

    def __init__(self, name: str, tl: "Timeline", memo_size: int=50, memo_type: str=None, wavelength=None, seed: int=None, component_templates: dict = {}, gate_fid: float = 1, meas_fid: float = 1):
        """Constructor for quantum router class.

        Args:
            name (str): label for node.
            tl (Timeline): timeline for simulation.
            memo_size (int): number of memories to add in the array (default 50).
            seed (int): the random seed for the random number generator
            compoment_templates (dict): parameters for the quantum router
            gate_fid (float): fidelity of multi-qubit gates (usually CNOT) that can be performed on the node;
                Default value is 1, meaning ideal gate.
            meas_fid (float): fidelity of single-qubit measurements (usually Z measurement) that can be performed on the node;
                Default value is 1, meaning ideal measurement.
        """

        super().__init__(name, tl, seed, gate_fid, meas_fid)
        if not component_templates:
            component_templates = {}

        # create memory array object with optional args
        self.memo_arr_name = name + ".MemoryArray"
        # memo_arr_args = component_templates.get("MemoryArray", {})
        self.memo_type = component_templates.get("memo_type", None)
        memory_array = MemoryArray(self.memo_arr_name, tl, num_memories=memo_size, memory_type = self.memo_type, wavelength=wavelength)
        self.add_component(memory_array)
        memory_array.add_receiver(self)

        # setup managers
        self.resource_manager = None
        self.network_manager = None
        self.init_managers(self.memo_arr_name)
        self.map_to_middle_node = {}
        self.app = None

        self.attempts = 0 # count of entanglemend attempts
        self.basis = None
        self.meas_results = {"X_11": 0, "X_22": 0, "X_33": 0, "X_44": 0, "Z_11": 0, "Z_22": 0, "Z_33": 0, "Z_44": 0}
        self.entanglement_time = None
        self.last_trap_time = 0
        self.need_to_retrap = False
        self.time_in_trap = 0
        self.ll = 0

    def receive_message(self, src: str, msg: "Message") -> None:
        """Determine what to do when a message is received, based on the msg.receiver.

        Args:
            src (str): name of node that sent the message.
            msg (Message): the received message.
        """

        log.logger.info("{} receive message {} from {}".format(self.name, msg, src))
        if msg.receiver == "network_manager":
            self.network_manager.received_message(src, msg)
        elif msg.receiver == "resource_manager":
            self.resource_manager.received_message(src, msg)
        else:
            if msg.receiver is None:  # the msg sent by EntanglementGenerationB doesn't have a receiver (EGA & EGB not paired)
                matching = [p for p in self.protocols if type(p) == msg.protocol_type]
                for p in matching:    # the valid_trigger_time() function resolves multiple matching issue
                    p.received_message(src, msg)
            else:
                for protocol in self.protocols:
                    if protocol.name == msg.receiver:
                        protocol.received_message(src, msg)
                        break

    def init_managers(self, memo_arr_name: str):
        """Initialize resource manager and network manager.

        Args:
            memo_arr_name (str): the name of the memory array.
        """
        resource_manager = ResourceManager(self, memo_arr_name)
        network_manager = NewNetworkManager(self, memo_arr_name)
        self.set_resource_manager(resource_manager)
        self.set_network_manager(network_manager)

    def set_resource_manager(self, resource_manager: ResourceManager):
        """Assigns the resource manager."""
        self.resource_manager = resource_manager

    def set_network_manager(self, network_manager: NetworkManager):
        """Assigns the network manager."""
        self.network_manager = network_manager

    def init(self):
        """Method to initialize quantum router node.

        Inherit parent function.
        """

        super().init()

    def add_bsm_node(self, bsm_name: str, router_name: str):
        """Method to record connected BSM nodes

        Args:
            bsm_name (str): the BSM node between nodes self and router_name.
            router_name (str): the name of another router connected with the BSM node.
        """
        self.map_to_middle_node[router_name] = bsm_name

    def get(self, photon: "Photon", **kwargs):
        """Receives photon from last hardware element (in this case, quantum memory)."""
        dst = kwargs.get("dst", None)
        if dst is None:
            raise ValueError("Destination should be supplied for 'get' method on QuantumRouter")
        self.send_qubit(dst, photon)

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive expired memories.

        Args:
            memory (Memory): memory that has expired.
        """

        self.resource_manager.memory_expire(memory)

    def set_app(self, app: "RequestApp"):
        """Method to add an application to the node."""

        self.app = app

    def reserve_net_resource(self, responder: str, start_time: int, end_time: int, memory_size: int,
                             target_fidelity: float, entanglement_number: int = 1, identity: int = 0) -> None:
        """Method to request a reservation.

        Can be used by local applications.

        Args:
            responder (str): name of the node with which entanglement is requested.
            start_time (int): desired simulation start time of entanglement.
            end_time (int): desired simulation end time of entanglement.
            memory_size (int): number of memories requested.
            target_fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement that the request ask for (default 1).
            identity (int): the ID of the request (default 0).
        """

        self.network_manager.request(responder, start_time, end_time, memory_size, target_fidelity, entanglement_number, identity)

    def get_idle_memory(self, info: "MemoryInfo") -> None:
        """Method for application to receive available memories."""

        if self.app:
            self.app.get_memory(info)

    def get_reservation_result(self, reservation: "Reservation", result: bool) -> None:
        """Method for application to receive reservations results

        Args:
            reservation (Reservation): the reservation created by the reservation protocol at this node (the initiator).
            result (bool): whether the reservation has been approved by the responder.
        """

        if self.app:
            self.app.get_reservation_result(reservation, result)

    def get_other_reservation(self, reservation: "Reservation"):
        """Method for application to add the approved reservation that is requested by other nodes
        
        Args:
            reservation (Reservation): the reservation created by the other node (this node is the responder)
        """

        if self.app:
            self.app.get_other_reservation(reservation)

    def save_measurement(self, psi_sign, measurement):
        # psi_sign is 1 for psi+ and -1 for psi-
        # measurement is length 2 list where each element is 0 (down) or 1 (up)

        # for PSI- we want to flip the sign of X_same and X_diff in our Fidelity formula
        # to do that, I am just flipping X_same and X_diff right here as they have opposite signs in the formula
        if psi_sign == -1 and self.basis == "X":
            if measurement[0] == 0:
                measurement[0] = 1
            elif measurement[0] == 1:
                measurement[0] = 0
            else:
                raise ValueError(f'Measurement result should be a bit, not {measurement[0]}')

        if measurement[0] == measurement[1] == 0: # \rho_11 in either basis
            self.meas_results[self.basis + '_11'] += 1
        elif measurement[0] == measurement[1] == 1: # \rho_44 in either basis
            self.meas_results[self.basis + '_44'] += 1
        elif (measurement[0] == 0) and (measurement[1] == 1): # \rho_22 in either basis
            self.meas_results[self.basis + '_22'] += 1
        elif (measurement[0] == 1) and (measurement[1] == 0): # \rho_33 in either basis
            self.meas_results[self.basis + '_33'] += 1
        else:
            raise ValueError(f'Measurement values should both be bits, not {measurement}.')

        self.entanglement_time = self.timeline.now()

    def get_fidelity(self):
        # fidelity calculation derived from:
        # https://static-content.springer.com/esm/art%3A10.1038%2Fnature12016/MediaObjects/41586_2013_BFnature12016_MOESM10_ESM.pdf
        # which is in supplementary information of this paper:
        # https://www.nature.com/articles/nature12016#Sec2

        # told measurements in X and Z bases respectively
        X_trials = sum(self.meas_results[f'X_{i}{i}'] for i in range(1,5))
        Z_trials = sum(self.meas_results[f'Z_{i}{i}'] for i in range(1,5))

        rhoX_diff = (self.meas_results[f'X_22']+self.meas_results[f'X_33'])/X_trials
        rhoX_same = (self.meas_results[f'X_11']+self.meas_results[f'X_44'])/X_trials
        rhoZ_diff = (self.meas_results[f'Z_22']+self.meas_results[f'Z_33'])/Z_trials # rho_22 + rho_33
        rhoZ_prod_same = (self.meas_results[f'Z_11']/Z_trials)*(self.meas_results[f'Z_44']/Z_trials) # rho_11*rho_44

        print(rhoX_diff)
        print(rhoX_same)
        print(rhoZ_diff)
        print(rhoZ_prod_same)

        f = self.meas_fid * (rhoZ_diff + rhoX_same - rhoX_diff - 2*sqrt(rhoZ_prod_same))/2
        return f