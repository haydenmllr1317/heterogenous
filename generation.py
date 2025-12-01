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
    from sequence.components.bsm import BSM
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
from sequence.constants import BARRET_KOK

class HetEGA(EntanglementGenerationA):

    # Desired Bell States
    _psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]
    _psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory"):

        super().__init__(owner, name, middle, other, memory)
        # self.protocol_type = "Het_EGA" # it's just going to defaul to BARRET_KOK which I think is fine

        self.early_bin = [-1, -1]
        self.late_bin = [-1, -1]

        self.detector_resolution = None
        
        self.early_click_types = [] # list of booleans determining whether early clicks were signals or not
        self.early_detectors = [] # list of detectors clicked in early time bin

        self.late_click_types = [] # list of booleans determining whether late clicks were signals or not
        self.late_detectors = [] # list of detectors clicked in late time bin

        self.emit_delay = None

    # this is to add detector resolution to our existing bins
    def update_bins(self, detector_resolution):
        self.early_bin = (self.early_bin[0] - (detector_resolution//2)), (self.early_bin[1] + (detector_resolution//2))
        self.late_bin = (self.late_bin[0] - (detector_resolution//2)), (self.late_bin[1] + (detector_resolution//2))

    def start(self) -> None:
        """Method to start heterogenous entanglement generation protocol.

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """

        self.memory.attempts += 1

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        # to avoid start after remove protocol
        if self not in self.owner.protocols:
            return

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            # time required by memory between excitation and emission:
            self.emit_delay = self.memory.initialize_time + self.memory.cool_time + self.memory.state_prep_time + self.memory.excite_pulse_time
            # how long memory has already been in trap:
            time_in_trap = self.owner.timeline.now() - self.owner.app.last_trap_time
            # check if we need to retrap (and do so if necessary):
            if self.owner.memo_type == 'Yb':
                if (self.memory.attempts == 1) or (time_in_trap >= self.memory.lifetime_reload_time) or (self.memory.wavelength == 1389 and (self.memory.attempts % self.memory.retrap_num) == 1):
                    self.memory.need_to_retrap = True
                    added_delay = self.memory.retrap_time
                    self.emit_delay += added_delay
                    for event in self.scheduled_events:
                        if event.process.activation == 'lose_atom':
                            self.owner.timeline.remove_event(event)
                    self.owner.app.last_trap_time = self.owner.timeline.now()

                    # schedule next atom loss event
                    assert self.memory.atom_lifetime > 0, f"Attempting to schedule atom loss for {self.memory.name} with 0 atom lifetime."
                    time_to_next = int(self.owner.get_generator().exponential(scale=self.memory.atom_lifetime))
                    time = time_to_next + self.owner.timeline.now() + self.memory.retrap_time
                    process = Process(self.memory, "lose_atom", [])
                    event = Event(time, process)
                    self.owner.timeline.schedule(event)
                    self.scheduled_events.append(event)
                
            bin_width = self.memory.bin_width
            bin_separation = self.memory.bin_separation
            message = HetEntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name, BARRET_KOK,
                                                    qc_delay=self.qc_delay, emit_delay=self.emit_delay, bin_width=bin_width, bin_separation=bin_separation)
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
            May reset this protocol's parameters
        """

        # to avoid start after protocol removed
        if self not in self.owner.protocols:
            return

        self.ent_round += 1

        if self.ent_round == 1:
            return True
        
        elif self.ent_round == 2:

            if (len(self.early_click_types) == 1) and (len(self.late_click_types) == 1): # one early and one late photon
                
                qm = self.owner.timeline.quantum_manager
                other_key = self.owner.timeline.get_entity_by_name(self.remote_memo_id).qstate_key #key of possibly entangled memory

                if self.early_detectors[0] == self.late_detectors[0]: # psi+
                    self.memory.psi_sign = 1
                else:                                                 # psi-
                    self.memory.psi_sign = -1

                if (self.early_click_types[0]==1) and (self.late_click_types[0]==1): # both signal photons
                    if self.memory.psi_sign == 1: # psi+
                        _set_state_with_fidelity([self.memory.qstate_key, other_key], self._psi_plus, 1.0, self.owner.get_generator(), qm) # NOTE hardcoded fidelity to 1.0
                    else:                         # psi-
                        _set_state_with_fidelity([self.memory.qstate_key, other_key], self._psi_minus, 1.0, self.owner.get_generator(), qm) # NOTE hardcoded fidelity to 1.0
                else:
                    log.logger.warning(f'False positive entanglement heralded with sources {self.early_click_types[0]},{self.late_click_types[0]}.')
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
        """Method to set up memory and excite it (for photon emission).

        Side Effects:
            May change state of attached memory.
            May cause attached memory to emit photon.
        """
        
        process = Process(self.memory, "excite", [self.middle])
        time = self.memory.initialize_cool_prep() + self.memory.excite_pulse_time
        assert time == self.emit_delay, \
        "Time to emission should equal memories emit delay, but doesn\'t {} {} {}".format(time, self.emit_delay, self.owner.timeline.now())
        event = Event(self.owner.timeline.now() + time, process)
        self.owner.timeline.schedule(event)
        self.scheduled_events.append(event)


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

        log.logger.debug("{} {} received message from node {} of type {}".format(
                         self.owner.name, self.name, src, msg.msg_type))

        if msg_type is GenerationMsgType.NEGOTIATE:  # primary -> non-primary

            # configure params
            other_qc_delay = msg.qc_delay
            self.qc_delay = self.owner.qchannels[self.middle].delay
            cc_delay = int(self.owner.cchannels[src].delay)
            total_quantum_delay = max(self.qc_delay, other_qc_delay)  # two qc_delays are the same for "meet_in_the_middle"

            # get time required after excitation before emission
            other_emit_delay = msg.emit_delay
            self.emit_delay = self.memory.initialize_time + self.memory.cool_time + self.memory.state_prep_time + self.memory.excite_pulse_time

            # how long memory has already been in trap:
            time_in_trap = self.owner.timeline.now() - self.owner.app.last_trap_time
            # check if we need to retrap (and do so if necessary):
            if self.owner.memo_type == "Yb":
                if (self.memory.attempts == 1) or (time_in_trap >= self.memory.lifetime_reload_time) or (self.memory.wavelength == 1389 and (self.memory.attempts % self.memory.retrap_num) == 1):
                    self.memory.need_to_retrap = True
                    added_delay = self.memory.retrap_time
                    self.emit_delay += added_delay
                    for event in self.scheduled_events:
                        if event.process.activation == 'lose_atom':
                            self.owner.timeline.remove_event(event)
                    self.owner.app.last_trap_time = self.owner.timeline.now()

                    # schedule next atom loss event
                    assert self.memory.atom_lifetime > 0, f"Attempting to schedule atom loss for {self.memory.name} with 0 atom lifetime."
                    time_to_next = int(self.owner.get_generator().exponential(scale=self.memory.atom_lifetime))
                    time = time_to_next + self.owner.timeline.now() + self.memory.retrap_time
                    process = Process(self.memory, "lose_atom", [])
                    event = Event(time, process)
                    self.owner.timeline.schedule(event)
                    self.scheduled_events.append(event)

            # get max emit delay
            total_emit_delay = max(other_emit_delay, self.emit_delay) # largest possible time for emission

            # get earliest possible time for first excite event
            min_time = self.owner.timeline.now() + total_quantum_delay - self.qc_delay + cc_delay  # cc_delay time for NEGOTIATE_ACK
            
            # schedule emission into quantum channel
            emit_time = self.owner.schedule_qubit(self.middle, min_time + total_emit_delay)

            total_bin_separation = max(self.memory.bin_separation, msg.bin_separation)
            total_bin_width = max(self.memory.bin_width, msg.bin_width)
            self.memory.bin_separation = total_bin_separation # set memory to max
            self.memory.bin_width = total_bin_width           # set memory to max

            # create bins
            self.expected_time = emit_time + self.qc_delay
            self.early_bin = [self.expected_time, (self.expected_time + total_bin_width)]
            self.late_bin = [self.early_bin[0] + total_bin_separation, (self.early_bin[1] + total_bin_separation)]
           
            # schedule start of emission process
            process = Process(self, "emit_event", [])
            begin_emit_event_time = emit_time - self.emit_delay # time we should beginning emission process
            event = Event(time=begin_emit_event_time, process=process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            other_emit_time = emit_time + self.qc_delay - other_qc_delay
            message = HetEntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, BARRET_KOK, emit_time=other_emit_time, total_bin_separation=total_bin_separation, total_bin_width=total_bin_width)
            self.owner.send_message(src, message)

            # schedule future update_memory
            # TODO: base future start time on resolution
            future_start_time = self.late_bin[1] + self.owner.cchannels[self.middle].delay + 1_000  # delay is for sending the BSM_RES to end nodes, 1ns is just tolerance
            process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:  # non-primary --> primary

            assert msg.total_bin_separation >= self.memory.bin_separation, \
                "Protocol bin separation must be >= each memory bin separation {} {} {}".format(total_bin_separation, self.memory.bin_separation, self.owner.timeline.now())

            assert msg.total_bin_width >= self.memory.bin_width, \
                "Protocol bin width must be >= each memory bin width {} {} {}".format(msg.total_bin_width, self.memory.bin_width, self.owner.timeline.now())
            
            self.memory.bin_separation = msg.total_bin_separation
            self.memory.bin_width = msg.total_bin_width

            # NOTE unsure if we need this, I don't think it could ever occur
            if msg.emit_time < self.owner.timeline.now():  # emit time calculated by the non-primary node
                msg.emit_time = self.owner.timeline.now()

            # schedule emit
            emit_time = self.owner.schedule_qubit(self.middle, msg.emit_time)
            assert emit_time == (msg.emit_time), \
                "Invalid eg emit times {} {} {}".format(emit_time, msg.emit_time, self.owner.timeline.now())
            
            # set bins
            self.early_bin = [msg.emit_time + self.qc_delay, msg.emit_time + self.qc_delay + msg.total_bin_width]
            self.late_bin = [self.early_bin[0] + msg.total_bin_separation, self.early_bin[1] + msg.total_bin_separation]

            # schedule start of emission process
            process = Process(self, "emit_event", [])
            begin_emit_event_time = emit_time - self.emit_delay # time we should beginning emission process
            event = Event(begin_emit_event_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # schedule future memory update
            # TODO: base future start time on detector resolution
            future_start_time = self.late_bin[1] + self.owner.cchannels[self.middle].delay + 1_000
            process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.MEAS_RES:  # from middle BSM to both non-primary and primary
            detector_num = msg.detector
            time = msg.time
            resolution = msg.resolution # detector resolution
            click_type = msg.click_type # 0 for noise, 1 for signal, 2 for dark count

            if click_type == None:
                raise ValueError('\'click_type\' should be an int, not None. Message must have not passed through kwargs.')

            log.logger.debug("{} received MEAS_RES={} at time={:,}, expected={:,}, resolution={}, click_type={}".format(
                             self.owner.name, detector_num, time, self.expected_time, resolution, click_type))

            if not self.detector_resolution: # only should occur once per attempt
                self.detector_resolution = resolution
                self.update_bins(resolution)

            # if click_type == 2:
            #     log.logger.info('Dark count')
            # elif click_type == 3:
            #     raise ValueError('shoudnt have decohere for yb')

            # early time bin
            if self.early_bin[0] <= time <= self.early_bin[1]:
                self.early_click_types.append(click_type)
                self.early_detectors.append(detector_num)
            # late time bin
            elif self.late_bin[0] <= time <= self.late_bin[1]:
                self.late_click_types.append(click_type)
                self.late_detectors.append(detector_num) 
            # neither time bin
            else:
                log.logger.info('Photon found outside a bin.')
        else:
            raise Exception("Invalid message {} received by EG on node {}".format(msg_type, self.owner.name))

    def _entanglement_succeed(self):
        log.logger.warning(self.owner.name + " successful entanglement of memory {}".format(self.memory))
        self.memory.entangled_memory["node_id"] = self.remote_node_name
        self.memory.entangled_memory["memo_id"] = self.remote_memo_id
        self.memory.fidelity = self.memory.raw_fidelity

        for event in self.scheduled_events:
            if event.process.activation == 'lose_atom' and event.time > (self.owner.timeline.now() + self.memory.measurement_time):
                self.owner.timeline.remove_event(event)

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)

    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(self.owner.name + " failed entanglement of memory {}".format(self.memory))
        self.update_resource_manager(self.memory, MemoryInfo.RAW)


class HetEGB(EntanglementGenerationB):
    """Entanglement generation protocol for BSM node in heterogenous quantum network.

    The HetEGB protocol should be instantiated on a BSM node.
    Instances will communicate with the HetEGA instance on neighboring quantum router nodes to generate entanglement.

    Attributes:
        own (BSMNode): node that protocol instance is attached to.
        name (str): label for protocol instance.
        others (List[str]): list of neighboring quantum router nodes
    """

    def bsm_update(self, bsm: "BSM", info: Dict[str, Any]):
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM): bsm object calling method.
            info (Dict[str, any]): information passed from bsm.
        """

        assert info['info_type'] == "BSM_res"

        res = info["res"]                               # which detector clicked
        time = info["time"]                             # at what time detector was click
        resolution = bsm.detectors[0].time_resolution   # resolution of detectors in BSM (assuming same)
        click_type = info['click_type']                 # type of detector click (0 -> noise, 1 -> signal, 2 -> detector dark count)

        for node in self.others:
            message = HetEntanglementGenerationMessage(GenerationMsgType.MEAS_RES, None,              # receiver is None (not paired)
                                                    HetEGA, detector=res, time=time, resolution=resolution, click_type=click_type)
            self.owner.send_message(node, message)