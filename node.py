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
    from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
    from sequence.components.memory import Memory
    from photon import Photon
    from sequence.app.request_app import RequestApp

from sequence.kernel.entity import Entity, ClassicalEntity
from sequence.components.memory import MemoryArray
from bsm import BSM, TimeBinBSM
from sequence.components.light_source import LightSource
from detector import Detector
from sequence.qkd.BB84 import BB84
from sequence.qkd.cascade import Cascade
from sequence.entanglement_management.generation import EntanglementGenerationB, EntanglementGenerationMessage
from sequence.resource_management.resource_manager import ResourceManager
from sequence.network_management.network_manager import NewNetworkManager, NetworkManager
from encoding import *
from sequence.topology.node import Node
from sequence.utils import log
from sequence.components.bsm import SingleAtomBSM, SingleHeraldedBSM, PolarizationBSM


class BSMNode(Node):
    """Bell state measurement node.

    This node provides bell state measurement and the EntanglementGenerationB protocol for entanglement generation.
    Creates a SingleAtomBSM object within local components.

    Attributes:
        name (str): label for node instance.
        timeline (Timeline): timeline for simulation.
        eg (EntanglementGenerationB): entanglement generation protocol instance.
    """

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

        # NOTE: CHANGES
        elif self.encoding_type == 'time_bin':
            bsm_args = component_templates.get("TimeBinBSM", {})
            bsm = TimeBinBSM(bsm_name, timeline, **bsm_args)
        # NOTE: CHANGES END

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