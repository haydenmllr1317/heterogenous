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
    from memory import Memory
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
# from sequence.entanglement_management.generation import EntanglementGenerationMessage
# from encoding import time_bin
from math import e


def valid_trigger_time(trigger_time: int, target_time: int, resolution: int) -> bool:
    """return True if the trigger time is valid, else return False."""
    lower = target_time - (resolution // 2)
    upper = target_time + (resolution // 2)
    return lower <= trigger_time <= upper


class GenerationMsgType(Enum):
    """Defines possible message types for entanglement generation."""

    NEGOTIATE = auto()
    NEGOTIATE_ACK = auto()
    MEAS_RES = auto()


class EntanglementGenerationMessage(Message):
    """Message used by entanglement generation protocols.

    This message contains all information passed between generation protocol instances.
    Messages of different types contain different information.

    Attributes:
        msg_type (GenerationMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        qc_delay (int): quantum channel delay to BSM node (if `msg_type == NEGOTIATE`).
        frequency (float): frequency with which local memory can be excited (if `msg_type == NEGOTIATE`).
        emit_time (int): time to emit photon for measurement (if `msg_type == NEGOTIATE_ACK`).
        res (int): detector number at BSM node (if `msg_type == MEAS_RES`).
        time (int): detection time at BSM node (if `msg_type == MEAS_RES`).
        resolution (int): time resolution of BSM detectors (if `msg_type == MEAS_RES`).
    """

    def __init__(self, msg_type: GenerationMsgType, receiver: str, protocol_type: EntanglementProtocol, **kwargs):
        super().__init__(msg_type, receiver)
        # self.protocol_type = EntanglementGenerationA
        self.protocol_type = protocol_type

        if msg_type is GenerationMsgType.NEGOTIATE:
            self.qc_delay = kwargs.get("qc_delay")
            self.frequency = kwargs.get("frequency")

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:
            self.emit_time = kwargs.get("emit_time")
            self.min_time = kwargs.get('min_time')

        elif msg_type is GenerationMsgType.MEAS_RES:
            self.detector = kwargs.get("detector")
            self.time = kwargs.get("time")
            self.resolution = kwargs.get("resolution")

        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(msg_type))

    def __repr__(self):
        if self.msg_type is GenerationMsgType.NEGOTIATE:
            return "type:{}, qc_delay:{}, frequency:{}".format(self.msg_type, self.qc_delay, self.frequency)
        elif self.msg_type is GenerationMsgType.NEGOTIATE_ACK:
            return "type:{}, emit_time:{}".format(self.msg_type, self.emit_time)
        elif self.msg_type is GenerationMsgType.MEAS_RES:
            return "type:{}, detector:{}, time:{}, resolution={}".format(self.msg_type, self.detector, 
                                                                         self.time, self.resolution)
        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(self.msg_type))

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

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", encoding, loop: str = False, retrap_num: int = 128):
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
        
        self.original_memory_efficiency = self.owner.original_mem_eff

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
        # self.attempts = 0

        # self.atom_lost = False
        self.retrap_num = retrap_num

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

        # self.attempts += 1

        self.owner.attempts += 1

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        # to avoid start after remove protocol
        if self not in self.owner.protocols:
            return

        if self.owner.attempts == 1:
            self.memory.efficiency = self.original_memory_efficiency
            self.owner.atom_lost = False


        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name, protocol_type=EntanglementGenerationTimeBin,
                                                    qc_delay=self.qc_delay, frequency=frequency)
            self.memory
            if self.owner.attempts == 1:
                send = Process(self.owner, 'send_message', [self.remote_node_name, message])
                send_event = Event(self.owner.timeline.now() + self.encoding['retrap_time'], send)
                self.owner.timeline.schedule(send_event)
                self.scheduled_events.append(send_event)
            else:
                # send NEGOTIATE message
                self.owner.send_message(self.remote_node_name, message)
            
        if self.owner.attempts == self.retrap_num:
            self.owner.attempts = 0

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
        
        if (not self.owner.atom_lost):
            prob_atom_lost = .9708
            if self.owner.generator.random() > prob_atom_lost:
                log.logger.info('Atom on ' + self.owner.name + ' lost in sequence attempt ' + str(self.owner.attempts))
                self.memory.efficiency = 0
                self.owner.atom_lost = True

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
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, EntanglementGenerationTimeBin, emit_time=other_emit_time)
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
            # resolution = msg.resolution
            resolution = 20000

            log.logger.debug("{} received MEAS_RES={} at time={:,}, expected={:,}, resolution={}, round={}".format(
                             self.owner.name, sign, time, self.expected_time, resolution, self.ent_round))
            if valid_trigger_time(time, self.expected_time, resolution):   
                # log.logger.warning("really got valid time.")   
                self.psi_sign = sign 
            else:
                log.logger.info('{} BSM trigger time not valid'.format(self.owner.name)) # CHANGED FROM WARNING TO INFO

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

        if self.primary:
            result, basis = self.memory.measure()
            rm1 = self.owner.timeline.get_entity_by_name('node1').resource_manager
            rm2 = self.owner.timeline.get_entity_by_name('node2').resource_manager
            rm1.fid_measurement(result, basis)
            rm2.fid_measurement(result, basis)
          

        a = 0
        for event in self.owner.timeline.events:
            if event.process.activation == 'add_dark_count':
                a += 1
            if event.process.activation != 'update_memory':
                self.owner.timeline.remove_event(event)
        
        # real_events = 0
        # for event in self.owner.timeline.events:
        #     if (not event._is_removed):
        #         real_events +=1

        # I don't think that this means anything
        # if real_events == 1:
        #     if a != 2:
        #         log.logger.warning('Dark count occured at ' + self.owner.name + '.')


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
            self.start()


class EntanglementGenerationTimeBinYb1389(EntanglementProtocol):
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

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", encoding, loop: str = False, retrap_num: int = 128):
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
        self.memories: List[Memory] = [memory]
        self.remote_memo_id: str = ""  # memory index used by corresponding protocol on other node
        
        # self.original_memory_efficiency = self.owner.original_mem_eff

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

        self.encoding = encoding
        
        # don't think we need this anymore
        # self.loop = loop # this is true if we want to continue gunning for entanglement

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

        self.owner.attempts += 1

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        # to avoid start after remove protocol
        if self not in self.owner.protocols:
            return

        if self.owner.attempts == 1:
            self.memory.efficiency = self.memory.original_memory_efficiency


        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name, EntanglementGenerationTimeBinYb1389,
                                                    qc_delay=self.qc_delay, frequency=frequency)
            self.memory
            if self.owner.attempts == 1:
                send = Process(self.owner, 'send_message', [self.remote_node_name, message])
                send_event = Event(self.owner.timeline.now() + self.memory.retrap_time, send)
                self.owner.timeline.schedule(send_event)
                self.scheduled_events.append(send_event)
            else:
                # send NEGOTIATE message
                self.owner.send_message(self.remote_node_name, message)
            
        if self.owner.attempts == self.memory.retrap_num:
            self.owner.attempts = 0

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
            # if self.psi_sign == 1 and not(self.primary):
            #     self.owner.timeline.quantum_manager.run_circuit(EntanglementGenerationTimeBin._z_circuit, [self._qstate_key])

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

        if self.ent_round != 1:
            raise ValueError('Entanglement protocol isn\'t single-heralded as desired.')
        
        process = Process(self.memory, "excite", ["time_bin", self.middle])
        event = Event(self.owner.timeline.now() + self.memory.initialize_cool_prep(), process)
        self.owner.timeline.schedule(event)
        self.scheduled_events.append(event)

        # if self.ent_round == 1:
        #     self.memory.update_state(EntanglementGenerationTimeBin._plus_state)
        # else:
        #     raise ValueError('Entanglement protocol isn\'t single-heralded as desired.')
        
        # if (not self.owner.atom_lost):
        #     prob_atom_lost = .9708
        #     if self.owner.generator.random() > prob_atom_lost:
        #         log.logger.info('Atom on ' + self.owner.name + ' lost in sequence attempt ' + str(self.owner.attempts))
        #         self.memory.efficiency = 0
        #         self.owner.atom_lost = True


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

            # NOTE NEED TO CHANGE THIS FROM EM_DELAY TO SOMETHING IN YB CLASS
            
            # get expected arrivel time of a late photon
            emit_delay = self.memory.initialize_time + self.memory.cool_time + self.memory.state_prep_time + self.memory.excite_pulse_time
            emit_time = self.owner.schedule_qubit(self.middle, min_time + emit_delay)  # used to send memory
            emit_time_delta = emit_time - min_time - emit_delay
            self.expected_time = emit_time + self.qc_delay + self.memory.bin_separation  # need to be prepared for worst case scenario - a late photon
           

            # schedule emit
            process = Process(self, "emit_event", [])
            event = Event(min_time + emit_time_delta, process) # NOTE changed to min_time from emit_time
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            other_emit_time = emit_time + self.qc_delay - other_qc_delay
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, EntanglementGenerationTimeBinYb1389, emit_time=other_emit_time, min_time=(min_time+emit_time_delta))
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
            emit_delay = self.memory.initialize_time + self.memory.cool_time + self.memory.state_prep_time + self.memory.excite_pulse_time
            self.expected_time = msg.emit_time + self.qc_delay + self.memory.bin_separation # expected time for middle BSM node to receive the photon
            # we include photon_bin_separation above as need to consider getting a photon in the 'late' state

            if msg.emit_time < self.owner.timeline.now():  # emit time calculated by the non-primary node
                msg.emit_time = self.owner.timeline.now()

            # schedule emit
            emit_time = self.owner.schedule_qubit(self.middle, msg.emit_time)
            assert emit_time == (msg.emit_time), \
                "Invalid eg emit times {} {} {}".format(emit_time, msg.emit_time, self.owner.timeline.now())

            process = Process(self, "emit_event", [])
            event = Event(msg.min_time, process)
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
                # log.logger.warning("really got valid time.")   
                self.psi_sign = sign 
            else:
                log.logger.info('{} BSM trigger time not valid'.format(self.owner.name)) # CHANGED FROM WARNING TO INFO

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
        log.logger.warning(self.owner.name + " successful entanglement of memory {}".format(self.memory))
        self.memory.entangled_memory["node_id"] = self.remote_node_name
        self.memory.entangled_memory["memo_id"] = self.remote_memo_id
        self.memory.fidelity = self.memory.raw_fidelity

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)

        for event in self.owner.timeline.events:
            if event.process.activation in ['add_dark_count', 'record_detection']:
                self.owner.timeline.remove_event(event)

        # if self.primary:
        #     result, basis = self.memory.measure()
        #     rm1 = self.owner.timeline.get_entity_by_name('node1').resource_manager
        #     rm2 = self.owner.timeline.get_entity_by_name('node2').resource_manager
        #     rm1.fid_measurement(result, basis)
        #     rm2.fid_measurement(result, basis)
          

        # a = 0
        # for event in self.owner.timeline.events:
        #     if event.process.activation == 'add_dark_count':
        #         a += 1
        #     if event.process.activation != 'update_memory':
        #         self.owner.timeline.remove_event(event)
        
        # real_events = 0
        # for event in self.owner.timeline.events:
        #     if (not event._is_removed):
        #         real_events +=1

        # I don't think that this means anything
        # if real_events == 1:
        #     if a != 2:
        #         log.logger.warning('Dark count occured at ' + self.owner.name + '.')


    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(self.owner.name + " failed entanglement of memory {}".format(self.memory))
        
        self.update_resource_manager(self.memory, MemoryInfo.RAW)

        # if self.loop:
        #     self.memory.reset()
        #     self.ent_round = 0  # keep track of current stage of protocol
        #     self.psi_sign = -1
        #     self.last_res = [0,-1]
        #     self.start()

class EntanglementGenerationTimeBinYb556(EntanglementProtocol):
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

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", encoding, loop: str = False, retrap_num: int = 128):
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
        self.photon_bin_separation = self.encoding['bin_separation']
        
        self.loop = loop # this is true if we want to continue gunning for entanglement
        # self.attempts = 0

        # self.atom_lost = False
        self.retrap_num = retrap_num

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

        # self.attempts += 1

        self.owner.attempts += 1

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        # to avoid start after remove protocol
        if self not in self.owner.protocols:
            return

        if self.owner.attempts == 1:
            self.memory.efficiency = self.original_memory_efficiency
            self.owner.atom_lost = False


        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name, EntanglementGenerationTimeBinYb556,
                                                    qc_delay=self.qc_delay, frequency=frequency)
            self.memory
            if self.owner.attempts == 1:
                send = Process(self.owner, 'send_message', [self.remote_node_name, message])
                send_event = Event(self.owner.timeline.now() + self.memory.retrap_time, send)
                self.owner.timeline.schedule(send_event)
                self.scheduled_events.append(send_event)
            else:
                # send NEGOTIATE message
                self.owner.send_message(self.remote_node_name, message)
            
        if self.owner.attempts == self.retrap_num:
            self.owner.attempts = 0

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
            # if self.psi_sign == 1 and not(self.primary):
            #     self.owner.timeline.quantum_manager.run_circuit(EntanglementGenerationTimeBin._z_circuit, [self._qstate_key])

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
        
        if (not self.owner.atom_lost):
            prob_atom_lost = .9708
            if self.owner.generator.random() > prob_atom_lost:
                log.logger.info('Atom on ' + self.owner.name + ' lost in sequence attempt ' + str(self.owner.attempts))
                self.memory.efficiency = 0
                self.owner.atom_lost = True

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
            emit_time = self.owner.schedule_qubit(self.middle, min_time + self.memory.emit_delay)  # used to send memory
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
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, EntanglementGenerationTimeBinYb556, emit_time=other_emit_time)
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
            # resolution = msg.resolution
            resolution = 20000

            log.logger.debug("{} received MEAS_RES={} at time={:,}, expected={:,}, resolution={}, round={}".format(
                             self.owner.name, sign, time, self.expected_time, resolution, self.ent_round))
            if valid_trigger_time(time, self.expected_time, resolution):   
                # log.logger.warning("really got valid time.")   
                self.psi_sign = sign 
            else:
                log.logger.info('{} BSM trigger time not valid'.format(self.owner.name)) # CHANGED FROM WARNING TO INFO

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

        if self.primary:
            result, basis = self.memory.measure()
            rm1 = self.owner.timeline.get_entity_by_name('node1').resource_manager
            rm2 = self.owner.timeline.get_entity_by_name('node2').resource_manager
            rm1.fid_measurement(result, basis)
            rm2.fid_measurement(result, basis)
          

        a = 0
        for event in self.owner.timeline.events:
            if event.process.activation == 'add_dark_count':
                a += 1
            if event.process.activation != 'update_memory':
                self.owner.timeline.remove_event(event)
        
        # real_events = 0
        # for event in self.owner.timeline.events:
        #     if (not event._is_removed):
        #         real_events +=1

        # I don't think that this means anything
        # if real_events == 1:
        #     if a != 2:
        #         log.logger.warning('Dark count occured at ' + self.owner.name + '.')


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
            self.start()

class EntanglementGenerationB(EntanglementProtocol):
    """Entanglement generation protocol for BSM node.

    The EntanglementGenerationB protocol should be instantiated on a BSM node.
    Instances will communicate with the A instance on neighboring quantum router nodes to generate entanglement.

    Attributes:
        own (BSMNode): node that protocol instance is attached to.
        name (str): label for protocol instance.
        others (List[str]): list of neighboring quantum router nodes
    """

    def __init__(self, owner: "BSMNode", name: str, others: List[str]):
        """Constructor for entanglement generation B protocol.

        Args:
            own (Node): attached node.
            name (str): name of protocol instance.
            others (List[str]): name of protocol instance on end nodes.
        """

        super().__init__(owner, name)
        assert len(others) == 2
        self.others = others  # end nodes

    def bsm_update(self, bsm: "SingleAtomBSM", info: Dict[str, Any]):
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM): bsm object calling method.
            info (Dict[str, any]): information passed from bsm.
        """

        assert info['info_type'] == "BSM_res"

        res = info["res"]
        time = info["time"]
        resolution = bsm.resolution

        for node in self.others:
            message = EntanglementGenerationMessage(GenerationMsgType.MEAS_RES, None,              # receiver is None (not paired)
                                                    EntanglementGenerationTimeBinYb1389, detector=res, time=time, resolution=resolution)
            self.owner.send_message(node, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        raise Exception("EntanglementGenerationB protocol '{}' should not "
                        "receive message".format(self.name))

    def start(self) -> None:
        pass

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        pass

    def is_ready(self) -> bool:
        return True

    def memory_expire(self, memory: "Memory") -> None:
        raise Exception("Memory expire called for EntanglementGenerationB protocol '{}'".format(self.name))