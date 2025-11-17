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
    from nodes import Node

from sequence.resource_management.memory_manager import MemoryInfo
from sequence.entanglement_management.generation.generation_base import EntanglementGenerationA, EntanglementGenerationB
from sequence.message import Message
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.circuit import Circuit
from sequence.utils import log
from sequence.entanglement_management.generation import GenerationMsgType
# from encoding import time_bin
from math import e, ceil
from sequence.components.bsm import _set_state_with_fidelity
from message import HetEntanglementGenerationMessage


def valid_trigger_time(trigger_time: int, target_time: int, resolution: int) -> bool:
    """return True if the trigger time is valid, else return False."""
    lower = target_time - (resolution // 2)
    upper = target_time + (resolution // 2)
    return lower <= trigger_time <= upper



class YbEGA(EntanglementGenerationA):
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

    # Desired Bell States
    _psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]
    _psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory", encoding, loop: str = False, retrap_num: int = 128):
        """Constructor for entanglement generation A class.

        Args:
            owner (Node): node to attach protocol to.
            name (str): name of protocol instance.
            middle (str): name of middle measurement node.
            other (str): name of other node.
            memory (Memory): memory to entangle.
        """

        super().__init__(owner, name, middle, other, memory)
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
        self.expected_time: int = -1   # expected time for late photon to arrive at detector

        # memory internal info
        self.ent_round = 0  # keep track of current stage of protocol
        self.psi_sign = None # 1 for psi^+ and -1 for psi^-
        self.last_res = [0,-1]  # keep track of bsm measurements to distinguish Psi+ and Psi-

        self.scheduled_events = []

        # misc
        self.primary: bool = False  # one end node is the "primary" that initiates negotiation

        self.encoding = encoding

        self.early_bin = -1, -1
        self.late_bin = -1, -1

        self.detector_resolution = None
        
        # don't think we need this anymore
        # self.loop = loop # this is true if we want to continue gunning for entanglement

        # # these lists are all updated in parity
        # self.trigger_times = [] # list of recent times when BSM clicked
        # self.signal_values = [] # list of booleans determining whether recent clicks were signals or not
        # self.photon_keys = [] # list of keys from recent photons that hit detectors (list element is None if detector dark count)
        # self.detector_hits = [] # list of recent detectors clicked

        #TODO 
        # make early/late click types into an enum for ease of reading/bug checking

        # these lists are all updated in parity
        # self.early_triggers = [] # list of times when BSM clicked within early time bin
        self.early_click_types = [] # list of booleans determining whether early clicks were signals or not
        self.early_detectors = [] # list of detectors clicked in early time bin

        # self.late_triggers = [] # list of times when BSM clicked within late time bin
        self.late_click_types = [] # list of booleans determining whether late clicks were signals or not
        self.late_detectors = [] # list of detectors clicked in late time bin

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

    # this is to add detector resolution to our existing bins
    def update_bins(self, detector_resolution):
        self.early_bin = (self.early_bin[0] - (detector_resolution//2)), (self.early_bin[1] + (detector_resolution//2))
        self.late_bin = (self.late_bin[0] - (detector_resolution//2)), (self.late_bin[1] + (detector_resolution//2))

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

        # if self.owner.attempts == 1:
        #     self.memory.efficiency = self.memory.original_memory_efficiency


        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = HetEntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name, YbEGA,
                                                    qc_delay=self.qc_delay, frequency=frequency)
            self.memory # TODO what does this do??
            # if self.owner.attempts == 1:
            #     send = Process(self.owner, 'send_message', [self.remote_node_name, message])
            #     send_event = Event(self.owner.timeline.now(), send)
            #     self.owner.timeline.schedule(send_event)
            #     self.scheduled_events.append(send_event)
            # else:
            #     # send NEGOTIATE message
            self.owner.send_message(self.remote_node_name, message)
            
    def _reset_params(self):
        
        self.detector_resolution = None

        self.early_click_types = [] # list of booleans determining whether early clicks were signals or not
        self.early_detectors = [] # list of detectors clicked in early time bin

        self.late_click_types = [] # list of booleans determining whether late clicks were signals or not
        self.late_detectors = [] # list of detectors clicked in late time bin


        
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
        
        elif self.ent_round == 2:
            # three things to consider:
            # psi parity (detector nums)
            # signal or not

            if len(self.late_click_types) == 2:
                self.owner.ll += 1

            if (len(self.early_click_types) == 1) and (len(self.late_click_types) == 1):
                qm = self.owner.timeline.quantum_manager

                other_key = self.owner.timeline.get_entity_by_name(self.remote_node_name).get_components_by_type("MemoryArray")[0].memories[0].qstate_key

                if self.early_detectors[0] == self.late_detectors[0]: # psi+
                    self.psi_sign = 1
                else: # psi-
                    self.psi_sign = -1

                if (self.early_click_types[0]==1) and (self.late_click_types[0]==1): # both signal photons
                    if self.psi_sign == 1: # psi+
                        _set_state_with_fidelity([self.memory.qstate_key, other_key], self._psi_plus, 1.0, self.owner.get_generator(), qm) # NOTE hardcoded fidelity to 1.0
                    else: # psi-
                        _set_state_with_fidelity([self.memory.qstate_key, other_key], self._psi_minus, 1.0, self.owner.get_generator(), qm) # NOTE hardcoded fidelity to 1.0
                else:
                    # print(self.owner.timeline.get_entity_by_name('BSM_0_1.BSM').measurement)
                    if (self.early_click_types[0] != 0) and (self.late_click_types[0] != 0):
                        raise ValueError('Unexpected cause of fake entanglement.')
                    log.logger.warning('False positive entanglement heralded.')
                # TODO really be conscientious about how we maintaing quantum keys when entanglement is faked
                # NOTE unsure if this is right, at some point must be thoughtful about how we hold the the states 
                # else: # the clicks aren't BOTH signals
                #     log.logger.info('Potential dark count state (correct timing interval).') 
                #     if self.early_click_types[0] != 2: # detector trigger comes from signal or QFC noise (NOT detector dark count)
                #         qm.set([self.early_qkeys[0]], self._plus_state)
                #     if self.late_click_types[0] != 2:
                #         qm.set([self.late_qkeys[0]], self._plus_state) # detector trigger comes from signal or QFC noise (NOT detector dark count)

                self._reset_params() # round is over, need to reset
                self._entanglement_succeed()
                return True
            else:
                log.logger.debug(f'Early and late time bins had {len(self.early_click_types)},{len(self.late_click_types)} clicks.')
                self._reset_params() # round is over, need to reset
                self._entanglement_fail()
                return False

        else:
            raise ValueError('Ent round should never reach 3')


    def emit_event(self) -> None:
        """Method to set up memory and emit photons.

        If the protocol is in round 1, the memory will be first set to the |+> state.
        Otherwise, it will apply an x_gate to the memory.
        Regardless of the round, the memory `excite` method will be invoked.

        Side Effects:
            May change state of attached memory.
            May cause attached memory to emit photon.
        """

        # log.logger.warning(f'Emit event occurs at {self.owner.timeline.now()}')

        if self.ent_round != 1:
            raise ValueError('Entanglement protocol isn\'t single-heralded as desired.')
        
        process = Process(self.memory, "excite", ["time_bin", self.middle])
        event = Event(self.owner.timeline.now() + self.memory.initialize_cool_prep() + self.memory.excite_pulse_time, process)
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


    def received_message(self, src: str, msg: HetEntanglementGenerationMessage) -> None:
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
            
            # get expected arrival time of an early photon
            emit_delay = self.memory.initialize_time + self.memory.cool_time + self.memory.state_prep_time + self.memory.excite_pulse_time

            time_in_trap = self.owner.timeline.now() - self.owner.last_trap_time

            if (self.owner.attempts == 1) or (time_in_trap >= self.memory.lifetime_reload_time) or (self.memory.wavelength == 1389 and (self.owner.attempts % self.memory.retrap_num) == 1):
                self.owner.need_to_retrap = True
                added_delay = self.memory.retrap_time
                emit_delay += added_delay
                for event in self.owner.timeline.events:
                    if event.process.activation in ['lose_atom']:
                        self.owner.timeline.remove_event(event)
                self.owner.last_trap_time = self.owner.timeline.now()

                assert self.memory.atom_lifetime > 0, f"Attempting to schedule atom loss for {self.memory.name} with 0 atom lifetime."
                time_to_next = int(self.owner.get_generator().exponential(self.memory.atom_lifetime) * 1e12)
                time = time_to_next + self.owner.timeline.now()
                process = Process(self.memory, "lose_atom", [])
                event = Event(time, process)
                self.owner.timeline.schedule(event)


            emit_time = self.owner.schedule_qubit(self.middle, min_time + emit_delay)  # used to send memory
            # self.owner.schedule_qubit(self.middle, emit_time + self.memory.bin_separation) ## NO LONGER NEED AS SENDING ONLY IN FIRST TIME BIN 
            # self.expected_time = emit_time + self.qc_delay + self.memory.bin_separation # need to be prepared for worst case scenario - a late photon
            self.early_bin = (emit_time + self.qc_delay), (emit_time + self.qc_delay + self.memory.bin_width)
            self.late_bin = (self.early_bin[0] + self.memory.bin_separation), (self.early_bin[1] + self.memory.bin_separation)
           

            # schedule emit
            process = Process(self, "emit_event", [])
            # CHANGED:
            begin_emit_event = emit_time - emit_delay
            event = Event(time=begin_emit_event, process=process)
            # event = Event(min_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            other_emit_time = emit_time + self.qc_delay - other_qc_delay
            message = HetEntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, YbEGA, emit_time=other_emit_time, min_time=min_time) # USED To BE min_time + emit_time_delta
            self.owner.send_message(src, message)


            # TODO: base future start time on resolution
            future_start_time = self.late_bin[1] + self.owner.cchannels[self.middle].delay + 1_000  # delay is for sending the BSM_RES to end nodes,

            process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:  # non-primary --> primary
            # configure params
            emit_delay = self.memory.initialize_time + self.memory.cool_time + self.memory.state_prep_time + self.memory.excite_pulse_time

            time_in_trap = self.owner.timeline.now() - self.owner.last_trap_time

            if (self.owner.attempts == 1) or (time_in_trap >= self.memory.lifetime_reload_time) or ((self.owner.attempts % self.memory.retrap_num) == 1 and self.memory.wavelength == 1389):
                self.owner.need_to_retrap = True
                added_delay = self.memory.retrap_time
                emit_delay += added_delay

                self.owner.last_trap_time = self.owner.timeline.now()
                
                assert self.memory.atom_lifetime > 0, f"Attempting to schedule atom loss for {self.memory.name} with 0 atom lifetime."
                time_to_next = int(self.owner.get_generator().exponential(self.memory.atom_lifetime) * 1e12)
                time = time_to_next + self.owner.timeline.now()
                process = Process(self.memory, "lose_atom", [])
                event = Event(time, process)
                self.owner.timeline.schedule(event)

            # self.expected_time = msg.emit_time + self.qc_delay + self.memory.bin_separation # expected time for middle BSM node to receive a late photon
            self.early_bin = (msg.emit_time + self.qc_delay), (msg.emit_time + self.qc_delay + self.memory.bin_width)
            self.late_bin = (self.early_bin[0] + self.memory.bin_separation), (self.early_bin[1] + self.memory.bin_separation)

            # we include photon_bin_separation above as need to consider getting a photon in the 'late' state

            if msg.emit_time < self.owner.timeline.now():  # emit time calculated by the non-primary node
                msg.emit_time = self.owner.timeline.now()

            # schedule emit
            emit_time = self.owner.schedule_qubit(self.middle, msg.emit_time)
            # self.owner.schedule_qubit(self.middle, msg.emit_time + self.memory.bin_separation) # NOT DOING ANYMORE
            assert emit_time == (msg.emit_time), \
                "Invalid eg emit times {} {} {}".format(emit_time, msg.emit_time, self.owner.timeline.now())

            process = Process(self, "emit_event", [])
            event = Event(msg.emit_time - emit_delay, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # schedule future memory update where we differentiate between psi+ and psi-
            # TODO: base future start time on resolution
            # NOTE: THERE USED TO BE A GAP OF 10 THAT I AM CHANGING TO 1000
            future_start_time = self.late_bin[1] + self.owner.cchannels[self.middle].delay + 1_000
            process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.MEAS_RES:  # from middle BSM to both non-primary and primary
            detector_num = msg.detector
            time = msg.time
            resolution = msg.resolution
            click_type = msg.click_type # 0 for noise, 1 for signal, 2 for dark count

            if click_type == None:
                raise ValueError('\'click_type\' should be an int, not None. Message must have not passed through kwargs.')


            log.logger.debug("{} received MEAS_RES={} at time={:,}, expected={:,}, resolution={}, round={}".format(
                             self.owner.name, detector_num, time, self.expected_time, resolution, self.ent_round))
            
            # steps for new valid time function:
            # 1. remove items from lists that are too old progressively
            # 2. if we have reached within bin width of expected time start checking:
            # 3. approve is there are 1 early and 1 late up to tolerance

            if not self.detector_resolution:
                self.detector_resolution = resolution
                self.update_bins(resolution)

            # early time bin
            if self.early_bin[0] <= time <= self.early_bin[1]:
                # self.early_triggers.append(time)
                # if click_type == 1:
                #     print(time - self.early_bin[0])
                #     pass
                self.early_click_types.append(click_type)
                self.early_detectors.append(detector_num)
                
            # late time bin
            elif self.late_bin[0] <= time <= self.late_bin[1]:
                if click_type == 1:
                    pass
                # self.late_triggers.append(time)
                self.late_click_types.append(click_type)
                self.late_detectors.append(detector_num) 
            else:
                log.logger.warning('Photon found outside a bin.')
                print('something funny happeing here')
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
            if event.process.activation in ['add_dark_count', 'record_detection', 'schedule_atom_loss', 'lose_atom']:
                self.owner.timeline.remove_event(event)

        time_to_measurement_results = self.owner.timeline.now() + self.memory.readout_time # current time + time it takes to measure
        if self.primary:
            result = self.memory.measure()
            process = Process(self.owner, "save_measurement", [self.psi_sign, result])
            if self.owner.basis == "X":
                time_to_measurement_results += self.memory.raman_half_pi_pulse_time
            event = Event(time_to_measurement_results, process)
            self.owner.timeline.schedule(event)
        
        self.owner.time_in_trap = time_to_measurement_results - self.owner.last_trap_time


    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(self.owner.name + " failed entanglement of memory {}".format(self.memory))
        
        self.update_resource_manager(self.memory, MemoryInfo.RAW)
class YbEGB(EntanglementGenerationB):
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

        super().__init__(owner, name, others)
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
        resolution = bsm.detectors[0].time_resolution

        for node in self.others:
            message = HetEntanglementGenerationMessage(GenerationMsgType.MEAS_RES, None,              # receiver is None (not paired)
                                                    YbEGA, detector=res, time=time, resolution=resolution, click_type=info['click_type'])
            self.owner.send_message(node, message)

    def received_message(self, src: str, msg: HetEntanglementGenerationMessage):
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