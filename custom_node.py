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
    from qchannels import QuantumChannel, ClassicalChannel
    from sequence.components.memory import Memory
    from photon import Photon
    from sequence.app.request_app import RequestApp

from sequence.kernel.entity import Entity, ClassicalEntity
from sequence.components.memory import MemoryArray
from time_bin_bsm import BSM, TimeBinBSM
from sequence.components.light_source import LightSource
from detector import Detector
from sequence.qkd.BB84 import BB84
from sequence.qkd.cascade import Cascade
from sequence.entanglement_management.generation import EntanglementGenerationB, EntanglementGenerationMessage
from sequence.resource_management.resource_manager import ResourceManager
from sequence.network_management.network_manager import NewNetworkManager, NetworkManager
from encoding import *
# from sequence.topology.node import Node
from sequence.utils import log
from sequence.components.bsm import SingleAtomBSM, SingleHeraldedBSM, PolarizationBSM


class Node(Entity):
    """Base node type that has both classical and quantum capabilties.
    
    Provides default interfaces for network.

    Attributes:
        name (str): label for node instance.
        timeline (Timeline): timeline for simulation.
        cchannels (Dict[str, ClassicalChannel]): mapping of destination node names to classical channel instances.
        qchannels (Dict[str, QuantumChannel]): mapping of destination node names to quantum channel instances.
        protocols (List[Protocol]): list of attached protocols.
        generator (np.random.Generator): random number generator used by node.
        components (Dict[str, Entity]): mapping of local component names to objects.
        first_component_name (str): name of component that first receives incoming qubits.
        gate_fid (float): fidelity of multi-qubit gates (usually CNOT) that can be performed on the node.
        meas_fid (float): fidelity of single-qubit measurements (usually Z measurement) that can be performed on the node.
    """

    def __init__(self, name: str, timeline: "Timeline", seed=None, gate_fid: float = 1, meas_fid: float = 1):
        """Constructor for node.

        name (str): name of node instance.
        timeline (Timeline): timeline for simulation.
        seed (int): seed for random number generator, default None
        """

        log.logger.info("Create Node {}".format(name))
        super().__init__(name, timeline)
        self.owner = self
        self.cchannels = {}  # mapping of destination node names to classical channels
        self.qchannels = {}  # mapping of destination node names to quantum channels
        self.protocols = []
        self.generator = np.random.default_rng(seed)
        self.components = {}
        self.first_component_name = None

        # note that we are assuming homogeneous gates and measurements,
        # i.e. every gate on one specific node has identical fidelity, and so is measurement.
        self.gate_fid = gate_fid
        self.meas_fid = meas_fid
        assert 0 <= gate_fid <= 1 and 0 <= meas_fid <= 1, "Gate fidelity and measurement fidelity must be between 0 and 1."

    def init(self) -> None:
        pass

    def set_seed(self, seed: int) -> None:
        self.generator = np.random.default_rng(seed)

    def get_generator(self) -> np.random.Generator:
        return self.generator

    def add_component(self, component: Entity) -> None:
        """Adds a hardware component to the node.

        Args:
            component (Entity): local hardware component to add.
        """

        self.components[component.name] = component
        component.owner = self

    def set_first_component(self, name: str):
        """set the name of component that first receives incoming qubits.

        Args:
            name (str): the name of component that first receives incoming qubits.
        """
        self.first_component_name = name

    def assign_cchannel(self, cchannel: "ClassicalChannel", another: str) -> None:
        """Method to assign a classical channel to the node.

        This method is usually called by the `ClassicalChannel.set_ends` method and not called individually.

        Args:
            cchannel (ClassicalChannel): channel to add.
            another (str): name of node at other end of channel.
        """

        self.cchannels[another] = cchannel

    def assign_qchannel(self, qchannel: "QuantumChannel", another: str) -> None:
        """Method to assign a quantum channel to the node.

        This method is usually called by the `QuantumChannel.set_ends` method and not called individually.

        Args:
            qchannel (QuantumChannel): channel to add.
            another (str): name of node at other end of channel.
        """

        self.qchannels[another] = qchannel

    def send_message(self, dst: str, msg: "Message", priority=inf) -> None:
        """Method to send classical message.

        Args:
            dst (str): name of destination node for message.
            msg (Message): message to transmit.
            priority (int): priority for transmitted message (default inf).
        """
        log.logger.info("{} send message {} to {}".format(self.name, msg, dst))

        if priority == inf:
            priority = self.timeline.schedule_counter
        self.cchannels[dst].transmit(msg, self, priority)

    def receive_message(self, src: str, msg: "Message") -> None:
        """Method to receive message from classical channel.

        Searches through attached protocols for those matching message, then invokes `received_message` method of protocol(s).

        Args:
            src (str): name of node sending the message.
            msg (Message): message transmitted from node.
        """
        log.logger.info("{} receive message {} from {}".format(self.name, msg, src))
        # signal to protocol that we've received a message
        if msg.receiver is not None:
            for protocol in self.protocols:
                if protocol.name == msg.receiver and protocol.received_message(src, msg):
                    return
        else:
            matching = [p for p in self.protocols if type(p) == msg.protocol_type]
            for p in matching:
                p.received_message(src, msg)

    def schedule_qubit(self, dst: str, min_time: int) -> int:
        """Interface for quantum channel `schedule_transmit` method."""

        return self.qchannels[dst].schedule_transmit(min_time)

    def send_qubit(self, dst: str, qubit) -> None:
        """Interface for quantum channel `transmit` method."""
        # print(len(self.qchannels[dst].send_bins))
        self.qchannels[dst].transmit(qubit, self)

    def receive_qubit(self, src: str, qubit) -> None:
        """Method to receive qubits from quantum channel.

        By default, forwards qubit to hardware element designated by field `receiver_name`.

        Args:
            src (str): name of node where qubit was sent from.
            qubit (any): transmitted qubit. Typically a Photon object.
        """

        self.components[self.first_component_name].get(qubit)

    def get_components_by_type(self, component_type: Union[str, type]) -> list:
        """Method to return all components of a specific type.
        Args:
            component_type (str/type): The type of components to filter for.
        Returns:
            list: A list of components matching the requested type.
        """
        if isinstance(component_type, str):
            return [comp for comp in self.components.values() if comp.__class__.__name__ == component_type]
        if isinstance(component_type, type):
            return [comp for comp in self.components.values() if isinstance(comp, component_type)]
        return []

    def change_timeline(self, timeline: "Timeline"):
        self.timeline = timeline
        for component in self.components.values():
            component.change_timeline(timeline)
        for cc in self.cchannels.values():
            cc.change_timeline(timeline)


class BSMNode(Node):
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
                 encoding, seed=None) -> None:
        """Constructor for BSM node.

        Args:
            name (str): name of node.
            timeline (Timeline): simulation timeline.
            other_nodes (List[str]): 2-member list of node names for adjacent quantum routers.
        """

        super().__init__(name, timeline, seed)
        # if not component_templates: # NOTE: NOT USING THIS ATM
        #     component_templates = {}

        # self.encoding_type = component_templates.get('encoding_type', 'single_atom') # NOTE: CHANGING THIS
        self.encoding = encoding
        self.encoding_type = self.encoding['name']

        # create BSM object with optional args
        bsm_name = name + ".BSM"
        if self.encoding_type == 'single_atom':
            # bsm_args = component_templates.get("SingleAtomBSM", {})
            bsm_args = {}
            bsm = SingleAtomBSM(bsm_name, timeline, **bsm_args)
        elif self.encoding_type == 'single_heralded':
            # bsm_args = component_templates.get("SingleHeraldedBSM", {})
            bsm_args = {}
            bsm = SingleHeraldedBSM(bsm_name, timeline, **bsm_args)
        elif self.encoding_type == 'time_bin' or self.encoding_type == 'yb_time_bin':
            # bsm_args = component_templates.get("TimeBinBSM", {})
            bsm_args = {}
            bsm = TimeBinBSM(bsm_name, timeline, self.encoding, **bsm_args)
        else:
            raise ValueError(f'Encoding type {self.encoding_type} not supported')

        self.add_component(bsm)
        self.set_first_component(bsm_name)

        self.eg = EntanglementGenerationB(self, "{}_eg".format(name), other_nodes)
        bsm.attach(self.eg)

    def receive_message(self, src: str, msg: "Message") -> None:
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if type(protocol) == msg.protocol_type:
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