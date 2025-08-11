"""Models for simulation of quantum memories.

This module defines the Memory class to simulate single atom memories as well as the MemoryArray class to aggregate memories.
Memories will attempt to send photons through the `send_qubit` interface of nodes.
Photons should be routed to a BSM device for entanglement generation, or through optical hardware for purification and swapping.
"""

from copy import copy
from math import inf
from typing import Any, List, TYPE_CHECKING, Dict, Callable, Union
from numpy import exp, array
from scipy import stats

if TYPE_CHECKING:
    from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
    from sequence.kernel.timeline import Timeline

from photon import Photon
from sequence.kernel.entity import Entity
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from encoding import single_atom, single_heralded, time_bin, yb_time_bin
from sequence.constants import EPSILON
from sequence.utils import log
from generation import EntanglementGenerationTimeBin as EGTB
from enum import Enum, auto
from sequence.components.circuit import Circuit

_meas_circuit = Circuit(2)
_meas_circuit.measure(0)
_meas_circuit.measure(1)
_H_circuit = Circuit(2)
_H_circuit.h(0)
_H_circuit.h(1)
# _sDag_circuit = Circuit(2)
# _sDag_circuit.sdg(0)
# _sDag_circuit.sdg(1)


# define helper functions for analytical BDS decoherence implementation, reference see recurrence protocol paper
def _p_id(x_rate, y_rate, z_rate, t):
    val = (1 + exp(-2*(x_rate+y_rate)*t) + exp(-2*(x_rate+z_rate)*t) + exp(-2*(z_rate+y_rate)*t)) / 4
    return val


def _p_xerr(x_rate, y_rate, z_rate, t):
    val = (1 - exp(-2*(x_rate+y_rate)*t) - exp(-2*(x_rate+z_rate)*t) + exp(-2*(z_rate+y_rate)*t)) / 4
    return val


def _p_yerr(x_rate, y_rate, z_rate, t):
    val = (1 - exp(-2*(x_rate+y_rate)*t) + exp(-2*(x_rate+z_rate)*t) - exp(-2*(z_rate+y_rate)*t)) / 4
    return val


def _p_zerr(x_rate, y_rate, z_rate, t):
    val = (1 + exp(-2*(x_rate+y_rate)*t) - exp(-2*(x_rate+z_rate)*t) - exp(-2*(z_rate+y_rate)*t)) / 4
    return val



class MemoryArray(Entity):
    """Aggregator for Memory objects.

    Equivalent to an array of single atom memories.
    The MemoryArray can be accessed as a list to get individual memories.

    Attributes:
        name (str): label for memory array instance.
        timeline (Timeline): timeline for simulation.
        memories (List[Memory]): list of all memories.
    """

    def __init__(self, name: str, timeline: "Timeline", num_memories=10,
                 memory_type = None, fidelity=0.85, frequency=80e6, efficiency=1,
                 coherence_time=-1, wavelength=500,
                 decoherence_errors: List[float] = None, cutoff_ratio = 1):
        """Constructor for the Memory Array class.

        Args:
            name (str): name of the memory array instance.
            timeline (Timeline): simulation timeline.
            num_memories (int): number of memories in the array (default 10).
            fidelity (float): fidelity of memories (default 0.85).
            frequency (float): maximum frequency of excitation for memories (default 80e6).
            efficiency (float): efficiency of memories (default 1).
            coherence_time (float): average time (in s) that memory state is valid (default -1 -> inf).
            wavelength (int): wavelength (in nm) of photons emitted by memories (default 500).
            decoherence_errors (List[int]): pauli decoherence errors. Passed to memory object.
            cutoff_ratio (float): the ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        """

        Entity.__init__(self, name, timeline)
        self.memories = []
        self.memory_name_to_index = {}
        self.memo_type = memory_type

        for i in range(num_memories):
            memory_name = self.name + f"[{i}]"
            self.memory_name_to_index[memory_name] = i
            if memory_type == 'Yb':
                memory = Yb(memory_name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength, decoherence_errors, cutoff_ratio)
            else:
                memory = Memory(memory_name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength, decoherence_errors, cutoff_ratio)
            memory.attach(self)
            self.memories.append(memory)
            memory.set_memory_array(self)

    def __getitem__(self, key: int) -> "Memory":
        return self.memories[key]

    def __setitem__(self, key: int, value: "Memory"):
        self.memories[key] = value

    def __len__(self) -> int:
        return len(self.memories)

    def init(self):
        """Implementation of Entity interface (see base class).

        Set the owner of memory as the owner of memory array.
        """

        for memory in self.memories:
            memory.owner = self.owner

    def memory_expire(self, memory: "Memory"):
        """Method to receive expiration events from memories.

        Args:
            memory (Memory): expired memory.
        """

        self.owner.memory_expire(memory)

    def update_memory_params(self, arg_name: str, value: Any) -> None:
        for memory in self.memories:
            memory.__setattr__(arg_name, value)

    def add_receiver(self, receiver: "Entity") -> None:
        """Add receiver to each memory in the memory array to receive photons.
        
        Args:
            receiver (Entity): receiver of the memory
        """
        for memory in self.memories:
            memory.add_receiver(receiver)

    def get_memory_by_name(self, name: str) -> "Memory":
        """Given the memory's name, get the memory object.
        
        Args:
            name (str): name of memory
        Return:
            (Memory): the memory object
        """
        index = self.memory_name_to_index.get(name, -1)
        assert index >= 0, "Oops! name={} not exist!"
        return self.memories[index]


class Memory(Entity):
    """Individual single-atom memory.

    This class models a single-atom memory, where the quantum state is stored as the spin of a single ion.
    This class will replace the older implementation once completed.

    Attributes:
        name (str): label for memory instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float):     (current) fidelity of memory.
        raw_fidelity (float): (initial) fidelity of memory.
        frequency (float): maximum frequency at which memory can be excited.
        efficiency (float): probability of emitting a photon when excited.
        coherence_time (float): average usable lifetime of memory (in seconds). Negative value means infinite coherence time.
        wavelength (float): wavelength (in nm) of emitted photons.
        qstate_key (int): key for associated quantum state in timeline's quantum manager.
        memory_array (MemoryArray): memory array aggregating current memory.
        entangled_memory (Dict[str, Any]): tracks entanglement state of memory.
        docoherence_errors (List[float]): assumeing the memory (qubit) decoherence channel being Pauli channel,
            Probability distribution of X, Y, Z Pauli errors;
            (default value is -1, meaning not using BDS or further density matrix representation)
            Question: is it general enough? Dephasing/damping channel, multipartite entanglement?
        cutoff_ratio (float): ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        generation_time (float): time when the EPR is first generated (float or int depends on timeing unit)
            (default -1 before generation or not used). Used only for logging
        last_update_time (float): last time when the EPR pair is updated (usually when decoherence channel applied),
            used to determine decoherence channel (default -1 before generation or not used)
        is_in_application (bool): whether the quantum memory is involved in application after successful distribution of EPR pair
    """

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int, decoherence_errors: List[float] = None, cutoff_ratio: float = 1):
        """Constructor for the Memory class.

        Args:
            name (str): name of the memory instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): initial fidelity of memory.
            frequency (float): maximum frequency of excitation for memory.
            efficiency (float): efficiency of memories.
            coherence_time (float): average time (in s) that memory state is valid.
            decoherence_rate (float): rate of decoherence to implement time dependent decoherence.
            wavelength (int): wavelength (in nm) of photons emitted by memories.
            decoherence_errors (List[float]): assuming the memory (qubit) decoherence channel being Pauli channel,
                probability distribution of X, Y, Z Pauli errors
                (default value is None, meaning not using BDS or further density matrix representation)
            cutoff_ratio (float): the ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        """

        super().__init__(name, timeline)
        assert 0 <= fidelity <= 1
        assert 0 <= efficiency <= 1

        self.fidelity = 0
        self.raw_fidelity = fidelity
        self.frequency = frequency
        self.efficiency = efficiency
        self.coherence_time = coherence_time  # coherence time in seconds
        self.decoherence_rate = 1 / self.coherence_time if self.coherence_time > 0 else 0 # rate of decoherence to implement time dependent decoherence
        self.wavelength = wavelength
        self.qstate_key = timeline.quantum_manager.new()
        self.memory_array = None

        self.decoherence_errors = decoherence_errors
        if self.decoherence_errors is not None:
                assert len(self.decoherence_errors) == 3 and abs(sum(self.decoherence_errors) - 1) < EPSILON, \
                "Decoherence errors refer to probabilities for each Pauli error to happen if an error happens, thus should be normalized."
        self.cutoff_ratio = cutoff_ratio
        assert 0 < self.cutoff_ratio <= 1, "Ratio of cutoff time and coherence time should be between 0 and 1"
        self.generation_time = -1
        self.last_update_time = -1
        self.is_in_application = False

        # for photons
        self.encoding = copy(single_atom)
        self.encoding["raw_fidelity"] = self.raw_fidelity

        # for photons in general single-heralded EG protocols
        self.encoding_sh = copy(single_heralded)

        # for photons with encoding type of time_bin
        self.encoding_tb = copy(time_bin)

        # for photons with yb time_bin encoding
        self.encoding_yb = copy(yb_time_bin)

        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of current memory write (ignore expiration of past states)
        self.expiration_event = None
        self.excited_photon = None

        self.next_excite_time = 0

    def init(self):
        pass

    def set_memory_array(self, memory_array: MemoryArray):
        self.memory_array = memory_array

    def excite(self, encoding_type, dst="", protocol="bk") -> None:
        """Method to excite memory and potentially emit a photon.

        If it is possible to emit a photon, the photon may be marked as null based on the state of the memory.

        Args:
            dst (str): name of destination node for emitted photon (default "").
            protocol (str): Valid values are "bk" (for Barrett-Kok protocol) or "sh" (for single heralded)

        Side Effects:
            May modify quantum state of memory.
            May schedule photon transmission to destination node.
        """

        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time:
            return

        # create photon
        if encoding_type == "time_bin":
            photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name, encoding_type=self.encoding_tb, 
            quantum_state=self.qstate_key, use_qm=True)
            # keep track of memory initialization time
            self.generation_time = self.timeline.now()
            self.last_update_time = self.timeline.now()
            self.encoding = self.encoing_tb
        if encoding_type == "yb_time_bin":
            photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name, encoding_type=self.encoding_yb, 
            quantum_state=self.qstate_key, use_qm=True)
            # keep track of memory initialization time
            self.generation_time = self.timeline.now()
            self.last_update_time = self.timeline.now()
            self.encoding = self.encoding_yb
        elif protocol == "bk":
            photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name, encoding_type=self.encoding,
                            quantum_state=self.qstate_key, use_qm=True)
        elif protocol == "sh":
            photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name, encoding_type=self.encoding_sh, 
                            quantum_state=self.qstate_key, use_qm=True)
            # keep track of initialization time
            self.generation_time = self.timeline.now()
            self.last_update_time = self.timeline.now()
        else:
            raise ValueError("Invalid protocol type {} specified for memory.exite()".format(protocol))

        photon.timeline = None  # facilitate cross-process exchange of photons
        photon.is_null = True
        photon.add_loss(1 - self.efficiency)

        if self.frequency > 0:
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        # emission = Process(self._receivers[0], 'get', [photon], {'dst': dst})
        # em_time = self.timeline.now() + self.encoding['em_delay']
        # em_event = Event(em_time, emission)
        # self.timeline.schedule(em_event)

        # send to receiver
        self._receivers[0].get(photon, dst=dst)
        self.excited_photon = photon

    def expire(self) -> None:
        """Method to handle memory expiration.

        Is scheduled automatically by the `set_plus` memory operation.

        If the quantum memory has been explicitly involved in application after entanglement distribution, do not expire.
            Some simplified applications do not necessarily need to modify the is_in_application attribute.
            Some more complicated applications, such as probe state preparation for distributed quantum sensing,
            may change is_in_application attribute to keep memory from expiring during study.
        
        Side Effects:
            Will notify upper entities of expiration via the `pop` interface.
            Will modify the quantum state of the memory.
        """

        if self.is_in_application:
            pass

        else:
            if self.excited_photon:
                self.excited_photon.is_null = True

            self.reset()
            # pop expiration message
            self.notify(self)

    def reset(self) -> None:
        """Method to clear quantum memory.

        Will reset quantum state to |0> and will clear entanglement information.

        Side Effects:
            Will modify internal parameters and quantum state.
        """

        self.fidelity = 0
        self.generation_time = -1
        self.last_update_time = -1

        self.timeline.quantum_manager.set([self.qstate_key], [complex(1), complex(0)])
        self.entangled_memory = {'node_id': None, 'memo_id': None}
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)
            self.expiration_event = None

    def update_state(self, state: List[complex]) -> None:
        """Method to set the memory state to an arbitrary pure state.

        Args:
            state (List[complex]): array of amplitudes for pure state in Z-basis.

        Side Effects:
            Will modify internal quantum state and parameters.
            May schedule expiration event.
        """

        self.timeline.quantum_manager.set([self.qstate_key], state)
        self.previous_bsm = -1
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # schedule expiration
        if self.coherence_time > 0:
            self._schedule_expiration()

    def bds_decohere(self) -> None:
        """Method to decohere stored BDS in quantum memory according to the single-qubit Pauli channels.

        During entanglement distribution (before application phase),
        BDS decoherence can be treated analytically (see entanglement purification paper for explicit formulae).

        Side Effects:
            Will modify BDS diagonal elements and last_update_time.
        """

        if self.decoherence_errors is None:
            # if not considering time-dependent decoherence then do nothing
            pass

        else:
            time = (self.timeline.now() - self.last_update_time) * 1e-12  # duration of memory idling (in s)
            if time > 0 and self.last_update_time > 0:  # time > 0 means time has progressed, self.last_update_time > 0 means the memory has not been reset

                x_rate, y_rate, z_rate = self.decoherence_rate * self.decoherence_errors[0], \
                                        self.decoherence_rate * self.decoherence_errors[1], \
                                        self.decoherence_rate * self.decoherence_errors[2]
                p_I, p_X, p_Y, p_Z = _p_id(x_rate, y_rate, z_rate, time), \
                                    _p_xerr(x_rate, y_rate, z_rate, time), \
                                    _p_yerr(x_rate, y_rate, z_rate, time), \
                                    _p_zerr(x_rate, y_rate, z_rate, time)

                state_now = self.timeline.quantum_manager.states[self.qstate_key].state  # current diagonal elements
                transform_mtx = array([[p_I, p_Z, p_X, p_Y],
                                       [p_Z, p_I, p_Y, p_X],
                                       [p_X, p_Y, p_I, p_Z],
                                       [p_Y, p_X, p_Z, p_I]])  # transform matrix for diagonal elements
                state_new = transform_mtx @ state_now  # new diagonal elements after decoherence transformation
            
                log.logger.debug(f'{self.name}: before f={state_now[0]:.6f}, after f={state_new[0]:.6f}')
                
                # update the quantum state stored in quantum manager for self and entangled memory
                keys = self.timeline.quantum_manager.states[self.qstate_key].keys
                self.timeline.quantum_manager.set(keys, state_new)

                # update the last_update_time of self
                # note that the attr of entangled memory should not be updated right now,
                # because decoherence has not been applied there
                self.last_update_time = self.timeline.now()

    def _schedule_expiration(self) -> None:
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)

        decay_time = self.timeline.now() + int(self.cutoff_ratio * self.coherence_time * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)

        self.expiration_event = event

    def update_expire_time(self, time: int):
        """Method to change time of expiration.

        Should not normally be called by protocols.

        Args:
            time (int): new expiration time.
        """

        time = max(time, self.timeline.now())
        if self.expiration_event is None:
            if time >= self.timeline.now():
                process = Process(self, "expire", [])
                event = Event(time, process)
                self.timeline.schedule(event)
        else:
            self.timeline.update_event_time(self.expiration_event, time)

    def get_expire_time(self) -> int:
        return self.expiration_event.time if self.expiration_event else inf

    def notify(self, msg: Dict[str, Any]):
        for observer in self._observers:
            observer.memory_expire(self)

    def detach(self, observer: 'EntanglementProtocol'):  # observer could be a MemoryArray
        if observer in self._observers:
            self._observers.remove(observer)

    def get_bds_state(self):
        """Method to get state of memory in BDS formalism.

        Will automatically call the `bds_decohere` method.
        """
        self.bds_decohere()
        state_obj = self.timeline.quantum_manager.get(self.qstate_key)
        state = state_obj.state
        return state

    def get_bds_fidelity(self) -> float:
        """Will get the fidelity from the BDS state

        Return:
            (float): the fidelity of the BDS state
        """
        state_obj = self.timeline.quantum_manager.get(self.qstate_key)
        state = state_obj.state
        return state[0]


class Yb1389States(Enum):
    S0 = float(-1) # for 1S0 state

    # the values of these three are their branching ratios
    P0 = 0.64 # for 3P0 state
    P1 = 0.35 # for 3P1 state
    P2 = 0.01 # for 3P2 state
    
    # arbitrary value now
    LOST = float(-2) # for atom fallen out of trap

class Yb556States(Enum):
    S0 = auto() # for 1S0 state
    LOST = auto() # for atom fallen out of trap


class Yb(Memory):

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int, decoherence_errors: List[float] = None, cutoff_ratio: float = 1):
        
        super().__init__(name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength, decoherence_errors, cutoff_ratio)

        self.original_memory_efficiency = self.efficiency

        self.retrap_time = 500_000_000_000
        
        if wavelength == 1389:
            self.initialize_time = 51_400_000
            self.cool_time = 1_400_000_000
            self.state_prep_time = 5_300_000
            self.excite_pulse_time = 16_000
            self.phase_flip_time = 700_000
            self.bin_gap = 2_100_000 # this is 2.8 microseconds separation minus 0.7microseconds raman pi pulse
            self.atom_state = Yb1389States.P0
            self.retrap_num = 128
        elif wavelength == 556:
            self.initialize_time = 20_000_000
            self.cool_time = 1_400_000_000
            self.state_prep_time = 850_000
            self.excite_pulse_time = 20_000
            self.phase_flip_time = 1_800_000
            self.bin_gap = 5_300_000 # this is 6 microseconds separation minus 0.7 microseconds raman pi pulse
            self.atom_state = Yb556States.S0
        else:
            raise ValueError('Wavelength ' + str(wavelength) + ' is not supported for ' + self.name + '.')
        
        self.bin_separation = self.excite_pulse_time + self.bin_gap + self.phase_flip_time


    def excite(self, encoding_type, dst="") -> None:

        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time:
            return
        
        wavelength = self.atom_transition()

        if wavelength != self.wavelength:
            log.logger.info('Photon with unideal wavelength of ' + str(wavelength) + ' emmited (wanted ' + str(self.wavelength) + ').')

        # create photon
        if encoding_type == "time_bin":
            yb_encoding = {'name': 'yb_time_bin', 'bin_separation': self.bin_separation, 'raw_fidelity': 1.0}
            photon = Photon("", self.timeline, wavelength=wavelength, location=self.name, encoding_type=yb_encoding, 
            quantum_state=self.qstate_key, use_qm=True) #TODO ADD A WAY TO POINT TOWARDS THE ACTUAL FOUR_VECTOR ENTANGLED STATE (FOR ATOM AND PHOTON)
            # keep track of memory initialization time
            self.generation_time = self.timeline.now()
            self.last_update_time = self.timeline.now()
            # self.encoding = self.encoding_tb
        else:
            raise ValueError("Invalid encoding type {} specified for memory.exite()".format(encoding_type))

        photon.timeline = None  # facilitate cross-process exchange of photons
        photon.is_null = True
        photon.add_loss(1 - self.efficiency)

        if self.frequency > 0:
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        # ADD: send to frequency converter

        # send to receiver
        self._receivers[0].get(photon, dst=dst)
        self.excited_photon = photon
    
    def initialize_cool_prep(self) -> int:

        if (self.owner.attempts == 1) or ((self.owner.attempts % 128) == 1 and self.wavelength == 1389):
            added_delay = self.retrap_time
            if self.wavelength == 1389:
                self.atom_state = Yb1389States.P0
                self.efficiency = self.original_memory_efficiency
        else:
            added_delay = 0

        # 3% loss due to depumping from 3P0 to 1S0
        if self.atom_state != Yb1389States.LOST and self.wavelength == 1389:
            if self.get_generator().random() >= .97:
                self.atom_state = Yb1389States.LOST
                self.efficiency = 0
                log.logger.info("Atom " + str(self.name) + " lost in depumping.")
            else:
                # if not lost, atoms should already be in correct state here
                if self.wavelength == 1389:
                    self.atom_state = Yb1389States.P0
        if self.efficiency != 0:
            self.update_state(EGTB._plus_state)
        log.logger.info('Atom ' + str(self.name) + ' succesfully prepared in |+>.')

        total_time = self.initialize_time + self.cool_time + self.state_prep_time + self.excite_pulse_time + added_delay
        return total_time
    
    def atom_transition(self) -> bool:
        # dict of decay states with a probability, wavelength tuple as the values
        if self.wavelength == 1389:
            if self.atom_state == Yb1389States.LOST:
                return None
            elif self.atom_state == Yb1389States.P0:
                if self.get_generator().random() <= Yb1389States.P0.value:
                    return 1389
                elif self.get_generator().random() <= (Yb1389States.P0.value + Yb1389States.P1.value):
                    self.atom_state = Yb1389States.S0
                    return 999
                else:
                    log.logger.info(f'Atom {self.name} lost in transition.')
                    self.atom_state = Yb1389States.LOST
                    self.efficiency = 0
                    return 999
            else:
                raise ValueError(f'Prior to transition, atom is incorrectly in {self.atom_state}.' )
        elif self.wavelength == 556:
            if self.atom_state == Yb556States.LOST:
                return None
            elif self.atom_state == Yb556States.S0:
                return 556
            else:
                raise ValueError(f'Prior to transition, atom is incorrectly in {self.atom_state}.' )
        else:
            raise ValueError('Wavelength ' + str(self.wavelength) + ' is not supported for ' + self.name + '.')
        
    def measure(self) -> float:
        # ideally this process is supressing the measured qubits state and forcing the key to point towards
        # the others'

        key0 = self.qstate_key
        key1 = self.timeline.get_entity_by_name(self.entangled_memory['node_id'] + '.MemoryArray[0]').qstate_key
        keys = [key0,key1]

        # print(self.timeline.quantum_manager.states[0].state)
        # if self.timeline.quantum_manager.states[0].state != self.timeline.quantum_manager.states[1].state:
        #     raise ValueError('soemthing weird')
        qm = self.timeline.quantum_manager

        for k in keys:
            if len(qm.states[k].state) != 4:
                log.logger.warning('dark count state')
                # qm.set([k], [1, 0])

        if self.owner.basis == "X":
            qm.run_circuit(_H_circuit, keys).keys()

        # if self.basis != 2:
        #     if self.basis == 1:
        #         qm.run_circuit(_sDag_circuit, keys)
        #     qm.run_circuit(_H_circuit, keys).keys()


        meas = qm.run_circuit(_meas_circuit, keys, self.get_generator().random())

        # now, we just care about whether they are the the same (0) or diff(1)

        if meas[key0] == meas[key1]:
            result = 0
        else:
            result = 1

        return result, self.owner.basis
    
    def change_wavelength(self, wavelength: int):
        if wavelength == 1389:
            self.initialize_time = 51_400_000
            self.cool_time = 1_400_000_000
            self.state_prep_time = 5_300_000
            self.excite_pulse_time = 16_000
            self.phase_flip_time = 700_000
            self.bin_gap = 2_100_000 # this is 2.8 microseconds separation minus 0.7microseconds raman pi pulse
            self.atom_state = Yb1389States.P0
            self.retrap_num = 128
        elif wavelength == 556:
            self.initialize_time = 20_000_000
            self.cool_time = 1_400_000_000
            self.state_prep_time = 850_000
            self.excite_pulse_time = 20_000
            self.phase_flip_time = 1_800_000
            self.bin_gap = 5_300_000 # this is 6 microseconds separation minus 0.7 microseconds raman pi pulse
            self.atom_state = Yb556States.S0
        else:
            raise ValueError('Wavelength ' + str(wavelength) + ' is not supported for ' + self.name + '.')
        
        self.wavelength = wavelength

    
class TState(Enum):
    g = auto()
    e = auto()
    f = auto()

class Transmon(Memory):
    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int, decoherence_errors: List[float] = None, cutoff_ratio: float = 1):
        
        super().__init__(name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength, decoherence_errors, cutoff_ratio)

        self.t1_coherance = 100000000
        self.t2_coherance = 100000000
        self.photon_collection_efficiency = 1 # uwaves emmited into cavity all get picked up
        self.wavelength = None # unclear what it is for uwave
        self.measurement_time = 1000000
        self.initialization_time = 5*self.t1_coherance # time to get everything into ground state
        self.prep_time = None # unclear what it is to apply hadamard pulse to ground state
        self.ge_transition_time = 20000 # time to excite from |g> -> |e>
        self.eg_transition_time = 20000 # time to excite from |e> -> |f>
        self.fe_transition_time = 200000 # time to drive decay from |f0> -> |g1>
        self.nondemolition_measurement_time = None # unclear how long this takes

        # TODO TState keep track of fidelity as isn't perfet

    def absorb(self, photon: Photon):
        # this should alter the state, taking a certain amount of time
        # TODO implement memory absorbtion 
        pass


