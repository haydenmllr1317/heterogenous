"""Code for Barrett-Kok entanglement Generation protocol

This module defines code to support entanglement generation between single-atom memories on distant nodes.
Also defined is the message type used by this implementation.
Entanglement generation is asymmetric:

* EntanglementGenerationA should be used on the QuantumRouter (with one node set as the primary) and should be started via the "start" method
* EntanglementGenerationB should be used on the BSMNode and does not need to be started
* EntanglementGenerationB should be used on the QuantumRoute (with on enode set as the primary) and should be started via the "start" method,
    it is the analog to EntanglementGenerationA, but with time_bin photons
"""

from __future__ import annotations
from enum import Enum, auto
from math import sqrt
from typing import List, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from sequence.components.memory import Memory
    from sequence.components.bsm import SingleAtomBSM
    from custom_node import Node

from sequence.resource_management.memory_manager import MemoryInfo
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.message import Message
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.circuit import Circuit
from sequence.utils import log
from sequence.entanglement_management.generation import GenerationMsgType
from sequence.entanglement_management.generation import EntanglementGenerationMessage
from encoding import time_bin
from math import e
import numpy as np
from numpy import random as rm


def valid_trigger_time(trigger_time: int, target_time: int, resolution: int) -> bool:
    """return True if the trigger time is valid, else return False."""
    lower = target_time - (resolution // 2)
    upper = target_time + (resolution // 2)
    return lower <= trigger_time <= upper

class EntanglementGenerationTimeBin(EntanglementProtocol):
    """Entanglement generation protocol for quantum router.

    The EntanglementGenerationTimeBin protocol should be instantiated on a quantum router node.
    Instances will communicate with each other (and with the B instance on a BSM node) to generate entanglement.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        middle (str): name of BSM measurement node where emitted photons should be directed.
        remote_node_name (str): name of distant QuantumRouter node, containing a memory to be entangled with local memory.
        remote_protocol_name (str): name of protocol on remote node
        memory (Memory): quantum memory object to attempt entanglement for.
        remote_memo_id (str): memory index used by corresponding protocol on
            other node
        fidelity(float): fidelity of memory protocol is attached to
        qc_delay(int): delay in quantum channel between node this protocol
            is on and the 'middle' node
        expected_time (int): expected time at which a 'late' photon would be
            detected
        ent_round (int): which round of enanglement we are on, as this is single
            heralded, there are only two rounds - entanglement and correction
        psi_sign (int): 0 if we have psi+, 1 if we have psi-, -1 if nothing
        last_res (List[int]): two element list, first element is the last time
            of a detector occurance, and the second is which detector was hit
        scheduled_events (List[Event]): list of future scheduled Event objects
        primary (bool): True if is unique primary node that initiates
            negotiations, False else
        _qstate_key (int): key from quantum manager for memory qubit state
        encoding_type (str): type of encoding for photons, set to "time_bin"
        photon_bin_separation (int): temporal separation between early and late
            photons, as specified in 'encoding' module under time_bin
    """

    _plus_state = [sqrt(1/2), sqrt(1/2)]
    _flip_circuit = Circuit(1)
    _flip_circuit.x(0)
    _z_circuit = Circuit(1)
    _z_circuit.z(0)

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", encoding, loop: str = False):
        """Constructor for entanglement generation A class.

        Args:
            owner (Node): node to attach protocol to.
            name (str): name of protocol instance.
            middle (str): name of middle measurement node.
            other (str): name of other node.
            memory (Memory): memory to entangle.
        """

        super().__init__(owner, name)
        self.middle: str = middle
        self.remote_node_name: str = other
        self.remote_protocol_name: str = None

        # memory info
        self.memory: Memory = memory
        self.remote_memo_id: str = ""  # memory index used by corresponding protocol on other node
        
        self.original_memory_efficiency = self.memory.efficiency

        # network and hardware info
        self.fidelity: float = memory.raw_fidelity
        self.qc_delay: int = 0
        self.expected_time: int = -1   # expected time for middle BSM node to receive the photon

        # memory internal info
        self.ent_round = 0  # keep track of current stage of protocol
        self.psi_sign = -1
        self.last_res = [0,-1]  # keep track of bsm measurements to distinguish Psi+ and Psi-

        self.scheduled_events = []

        # misc
        self.primary: bool = False  # one end node is the "primary" that initiates negotiation

        self._qstate_key: int = self.memory.qstate_key

        self.encoding = encoding
        self.encoding_type = self.encoding['name']
        self.photon_bin_separation = self.encoding['bin_separation']
        
        self.loop = loop # this is true if we want to continue gunning for entanglement
        self.attempts = 0

        self.atom_lost = False

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """
        assert self.remote_protocol_name is None
        self.remote_protocol_name = protocol
        self.remote_memo_id = memories[0]
        self.primary = self.owner.name > self.remote_node_name

    def start(self) -> None:
        """Method to start "one round" in the entanglement generation protocol (there are two rounds in Barrett-Kok).

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """

        self.attempts += 1

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        # to avoid start after remove protocol
        if self not in self.owner.protocols:
            return

        if (not self.atom_lost):
            prob_atom_lost = e**(-self.attempts/40)
            if np.random.rand() > prob_atom_lost:
                log.logger.info('Atom on ' + self.owner.name + ' lost in sequence attempt ' + str(self.attempts))
                self.memory.efficiency = 0
                self.atom_lost = True

        # if self.atom_lost:
        #     self._entanglement_fail()

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name,
                                                    qc_delay=self.qc_delay, frequency=frequency)
            self.memory
            if self.attempts == 1:
                send = Process(self.owner, 'send_message', [self.remote_node_name, message])
                send_event = Event(self.owner.timeline.now() + self.encoding['retrap_time'], send)
                self.owner.timeline.schedule(send_event)
                self.scheduled_events.append(send_event)
            else:
                # send NEGOTIATE message
                self.owner.send_message(self.remote_node_name, message)
            
        if self.attempts == 128:
            self.memory.efficiency = self.original_memory_efficiency
            self.attempts = 0
            self.atom_lost = False

    def update_memory(self) -> bool:
        """Method to handle necessary memory operations.

        Called on both nodes.
        Will check the state of the memory and protocol.

        Returns:
            bool: if current round was successfull.

        Side Effects:
            May change state of attached memory.
            May update memory state in the attached node's resource manager.
        """

        # to avoid start after protocol removed
        if self not in self.owner.protocols:
            return

        self.ent_round += 1

        if self.ent_round == 1:
            return True
        
        elif self.ent_round == 2 and self.psi_sign != -1:
            # entanglement succeeded, correction
            if self.psi_sign == 1 and not(self.primary):
                self.owner.timeline.quantum_manager.run_circuit(EntanglementGenerationTimeBin._z_circuit, [self._qstate_key])
            # if (not self.primary):
            #     print(self.owner.timeline.quantum_manager.states[self._qstate_key])
            #     print('aboves psi sign' + str(self.psi_sign))
            self._entanglement_succeed()
            return False

        else:
            # entanglement failed
            if self.ent_round != 2:
                raise ValueError('Ent Round should be 2 but is' + str(self.ent_round))
            self._entanglement_fail()

            return False


    def emit_event(self) -> None:
        """Method to set up memory and emit photons.

        If the protocol is in round 1, the memory will be first set to the |+> state.
        Otherwise, it will apply an x_gate to the memory.
        Regardless of the round, the memory `excite` method will be invoked.

        Side Effects:
            May change state of attached memory.
            May cause attached memory to emit photon.
        """

        if self.ent_round == 1:
            self.memory.update_state(EntanglementGenerationTimeBin._plus_state)
        else:
            raise ValueError('Entanglement protocol isn\'t single-heralded as desired.')
        self.memory.excite(self.encoding_type, self.middle)

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        """Method to receive messages.

        This method receives messages from other entanglement generation protocols.
        Depending on the message, different actions may be taken by the protocol.

        Args:
            src (str): name of the source node sending the message.
            msg (EntanglementGenerationMessage): message received.

        Side Effects:
            May schedule various internal and hardware events.
        """
        if src not in [self.middle, self.remote_node_name]:
            return
        msg_type = msg.msg_type

        log.logger.debug("{} {} received message from node {} of type {}, round={}".format(
                         self.owner.name, self.name, src, msg.msg_type, self.ent_round))

        if msg_type is GenerationMsgType.NEGOTIATE:  # primary -> non-primary
            # configure params
            other_qc_delay = msg.qc_delay
            self.qc_delay = self.owner.qchannels[self.middle].delay
            cc_delay = int(self.owner.cchannels[src].delay)
            total_quantum_delay = max(self.qc_delay, other_qc_delay)  # two qc_delays are the same for "meet_in_the_middle"

            # get time for first excite event
            memory_excite_time = self.memory.next_excite_time
            min_time = max(self.owner.timeline.now(), memory_excite_time) + total_quantum_delay - self.qc_delay + cc_delay  # cc_delay time for NEGOTIATE_ACK

            # NOTE: CHANGING THESE TWO LINES
            emit_time = self.owner.schedule_qubit(self.middle, min_time + self.encoding['em_delay'])  # used to send memory
            self.expected_time = emit_time + self.qc_delay + self.photon_bin_separation  # need to be prepared for worst case scenario - a late photon
           
            # emit_time = self.owner.schedule_qubit(self.middle, min_time + self.encoding['em_delay'])  # used to send memory
            # self.expected_time = self.qc_delay + self.photon_bin_separation + self.encoding['em_delay']  # need to be prepared for worst case scenario - a late photon
            # NOTE: CHANGES ARE FINISHED

            # schedule emit
            process = Process(self, "emit_event", [])
            event = Event(emit_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            other_emit_time = emit_time + self.qc_delay - other_qc_delay
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, emit_time=other_emit_time)
            self.owner.send_message(src, message)


            # TODO: base future start time on resolution
            # NOTE: THERE USED TO BE A +10 gap I am getting rid of here
            future_start_time = self.expected_time + self.owner.cchannels[self.middle].delay  # delay is for sending the BSM_RES to end nodes, 10 is a small gap
            # NOTE: CHANGING THIS TO MAKE IT SINGLE HERALDED
            process = Process(self, "update_memory", [])

            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:  # non-primary --> primary
            # configure params
            self.expected_time = msg.emit_time + self.qc_delay + self.photon_bin_separation # expected time for middle BSM node to receive the photon
            # we include photon_bin_separation above as need to consider getting a photon in the 'late' state

            if msg.emit_time < self.owner.timeline.now():  # emit time calculated by the non-primary node
                msg.emit_time = self.owner.timeline.now()

            # schedule emit
            emit_time = self.owner.schedule_qubit(self.middle, msg.emit_time)
            assert emit_time == (msg.emit_time), \
                "Invalid eg emit times {} {} {}".format(emit_time, msg.emit_time, self.owner.timeline.now())

            process = Process(self, "emit_event", [])
            event = Event(emit_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # schedule future memory update where we differentiate between psi+ and psi-
            # TODO: base future start time on resolution
            # NOTE: THERE USED TO BE A GAP OF 10 THAT I AM GETTING RID OF HERE
            future_start_time = self.expected_time + self.owner.cchannels[self.middle].delay
            process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.MEAS_RES:  # from middle BSM to both non-primary and primary
            sign = msg.detector # 0 if same detectors (psi+), 1 if different (psi-)
            time = msg.time
            resolution = msg.resolution

            log.logger.debug("{} received MEAS_RES={} at time={:,}, expected={:,}, resolution={}, round={}".format(
                             self.owner.name, sign, time, self.expected_time, resolution, self.ent_round))
            if valid_trigger_time(time, self.expected_time, resolution):      
                self.psi_sign = sign 
            else:
                log.logger.debug('{} BSM trigger time not valid'.format(self.owner.name))

        else:
            raise Exception("Invalid message {} received by EG on node {}".format(msg_type, self.owner.name))

    def is_ready(self) -> bool:
        return self.remote_protocol_name is not None

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive expired memories."""

        assert memory == self.memory

        self.update_resource_manager(memory, MemoryInfo.RAW)
        for event in self.scheduled_events:
            if event.time >= self.owner.timeline.now():
                self.owner.timeline.remove_event(event)

    def _entanglement_succeed(self):
        log.logger.info(self.owner.name + " successful entanglement of memory {}".format(self.memory))
        self.memory.entangled_memory["node_id"] = self.remote_node_name
        self.memory.entangled_memory["memo_id"] = self.remote_memo_id
        self.memory.fidelity = self.memory.raw_fidelity

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)

        a = 0
        for event in self.owner.timeline.events:
            if event.process.activation == 'add_dark_count':
                a += 1
            if event.process.activation != 'update_memory':
                self.owner.timeline.remove_event(event)
        real_events = 0
        for event in self.owner.timeline.events:
            if (not event._is_removed):
                real_events +=1

        if real_events == 1:
            if a != 2:
                log.logger.warning('Dark count occured at ' + self.owner.name + '.')


    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(self.owner.name + " failed entanglement of memory {}".format(self.memory))
        
        self.update_resource_manager(self.memory, MemoryInfo.RAW)

        if self.loop:
            self.memory.reset()
            self.ent_round = 0  # keep track of current stage of protocol
            self.psi_sign = -1
            self.last_res = [0,-1]
            self.atom_lost = False
            self.start()