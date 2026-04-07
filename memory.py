# TODO describe module

from typing import Any, List, TYPE_CHECKING
from numpy import exp, array

if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline

from photon import Photon
from sequence.kernel.entity import Entity
<<<<<<< HEAD
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from encoding import single_atom, single_heralded, yb_time_bin#, time_bin
from sequence.constants import EPSILON
from sequence.utils import log
from sequence.components.memory import MemoryArray
from generation import EntanglementGenerationTimeBin
from sequence.components.circuit import Circuit
=======
from sequence.constants import EPSILON
from sequence.utils import log
# from generation import EntanglementGenerationTimeBin as EGTB
from enum import Enum, auto
from sequence.components.circuit import Circuit
from sequence.components.bsm import _set_state_with_fidelity
from sequence.components.memory import Memory, MemoryArray
from math import sqrt, e

_meas_circuit = Circuit(2)
_meas_circuit.measure(0)
_meas_circuit.measure(1)
_H_circuit = Circuit(2)
_H_circuit.h(0)
_H_circuit.h(1)
# _sDag_circuit = Circuit(2)
# _sDag_circuit.sdg(0)
# _sDag_circuit.sdg(1)
_psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]

_photon_meas_circuit = Circuit(1)
_photon_meas_circuit.measure(0)
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec


class HetMemoryArray(MemoryArray):
    """Aggregator for Memory objects in heterogenous network.

<<<<<<< HEAD
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

_meas_circuit = Circuit(2)
_meas_circuit.measure(0)
_meas_circuit.measure(1)
_H_circuit = Circuit(2)
_H_circuit.h(0)
_H_circuit.h(1)
_sDag_circuit = Circuit(2)
_sDag_circuit.sdg(0)
_sDag_circuit.sdg(1)


class Memory(Entity):
    """Individual single-atom memory.

    This class models a single-atom memory, where the quantum state is stored as the spin of a single ion.
    This class will replace the older implementation once completed.
=======
    Equivalent to an array of single atom memories.
    The MemoryArray can be accessed as a list to get individual memories.
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec

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

<<<<<<< HEAD
        self.fidelity = 0
        self.raw_fidelity = fidelity
        self.frequency = frequency
        self.efficiency = efficiency
        self.coherence_time = coherence_time  # coherence time in seconds
        self.decoherence_rate = 1 / self.coherence_time if self.coherence_time > 0 else 0 # rate of decoherence to implement time dependent decoherence
        self.wavelength = wavelength
        self.qstate_key = timeline.quantum_manager.new()
        self.memory_array = None
        
        self.atom_present = True
=======
        for i in range(num_memories):
            memory_name = self.name + f"[{i}]"
            self.memory_name_to_index[memory_name] = i
            if memory_type == 'Yb':
                memory = Yb(memory_name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength)
            elif memory_type == 'uW':
                memory = uW(memory_name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength)
            else:
                raise ValueError('Heterogenous networks only accept Yb or uW memories currently.')
            memory.attach(self)
            self.memories.append(memory)
            memory.set_memory_array(self)
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec

class Yb1389States(Enum):
    S0 = auto()
    P0 = auto()
    LOST = auto()

class Yb556States(Enum):
    S0 = auto() # for 1S0 state
    LOST = auto() # for atom fallen out of trap

<<<<<<< HEAD
        # for photons in general single-heralded EG protocols
        self.encoding_sh = copy(single_heralded)

        # for photons with encoding type of time_bin
        # self.encoding_tb = copy(time_bin)

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

        self.basis = 0 # basis we are measuring in this round (for fidelity)
        #   0 == "X"
        #   1 == "Y"
        #   2 == "Z"

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
    
    def measure(self) -> float:
        key0 = self.qstate_key
        key1 = self.timeline.get_entity_by_name(self.entangled_memory['node_id'] + '.memo').qstate_key
        keys = [key0,key1]

        # print(self.timeline.quantum_manager.states[0].state)
        # if self.timeline.quantum_manager.states[0].state != self.timeline.quantum_manager.states[1].state:
        #     raise ValueError('soemthing weird')
        qm = self.timeline.quantum_manager

        for k in keys:
            if len(qm.states[k].state) != 4:
                log.logger.warning('dark count state')
                qm.set([k], [1, 0])

        if self.basis != 2:
            if self.basis == 1:
                qm.run_circuit(_sDag_circuit, keys)
            qm.run_circuit(_H_circuit, keys).keys()


        meas = qm.run_circuit(_meas_circuit, keys, self.get_generator().random())

        if meas[key0] == meas[key1]:
            result = 1
        else:
            result = -1

        return result, self.basis
=======
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec

class Yb(Memory):

    _plus_state = [sqrt(1/2), sqrt(1/2)]
    _minus_state = [sqrt(1/2), -sqrt(1/2)]
    _zero_ket = [1,0]

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int):
        
        super().__init__(name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength)

        # wavelength, coherence, efficiency: 3

        self.original_memory_efficiency = self.efficiency

        self.counter = 0
        self.time_after_excitement = None

        self.retrap_time = 500_000_000_000 #4 step1
        self.psi_sign = None # 1 for psi+, -1 for psi-
        self.attempts = 0
        self.need_to_retrap = False

        self.initialize_time = None          #5 step2
        self.cool_time = None                #6 step3
        self.clock_pulse_time = None         #7 step4(a)
        self.raman_half_pi_pulse_time = None #8 step4(b)
        self.state_prep_time = None
        self.excite_pulse_time = None        #9 step5(a)
        self.bin_width = None                #10 step5(b) detection window
        self.bin_gap = None
        self.phase_flip_time = None          #11 step5(c)
        self.bin_separation = None           #12 step5(d)
    
        self.atom_state = None               #13
        self.retrap_num = None               #14
        self.to_x_basis_time = None
        self.measurement_time = None         #15 step6
        self.state_lifetime = None           #16
        self.atom_lifetime = None            #17
        self.lifetime_reload_time = None     #18
        
        self.S0_decay = 0.354     ###0.133   #19 1S0 branching proportion
        self.P0_decay = 0.637     ###0.863   #20 3P0 branching proportion
        self.LOST_decay = 0.009   ###0.003   #21 LOST branching proportion
        self.measurement_fidelity = 0.995    #22 is readout fidelity (set to 99.5)
        #################################    #23 for 2-qubit gate fidelity
        #################################    #24 for CX + Hadamard gate time

        # TODO what is 2-qubit gate fidelity? (0.997 is Infleqtion's result, 0.995 might be good default)


    def excite(self, dst="") -> None:

        self.time_after_excitement = self.owner.timeline.now() + self.bin_separation # used for decoherence during round trip
        
        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time: # TODO can we initialize frequency as Inf?
            return
        
        wavelength = self.atom_transition()

        if wavelength != self.wavelength:
            log.logger.info('Photon with unideal wavelength of ' + str(wavelength) + ' emmited (wanted ' + str(self.wavelength) + ').')


        # yb_encoding = {'name': 'yb_time_bin', 'bin_separation': self.bin_separation, 'raw_fidelity': 1.0}
        yb_encoding = {'name': 'yb_time_bin'}
        photon = Photon("", self.timeline, wavelength=wavelength, location=self.name, encoding_type=yb_encoding, 
        quantum_state=self.qstate_key, use_qm=True) #TODO ADD A WAY TO POINT TOWARDS THE ACTUAL FOUR_VECTOR ENTANGLED STATE (FOR ATOM AND PHOTON)
        # keep track of memory initialization time
        # self.generation_time = self.timeline.now() # commented this out cuz I don't think we need
        # self.last_update_time = self.timeline.now() # commented this out cuz don't think we need

        photon.timeline = None  # facilitate cross-process exchange of photons
        photon.is_null = True

        # if photon.loss != 0:
        #     raise ValueError(f'{photon.name} just created, should have zero loss, not {photon.loss}.')

        if self.frequency > 0: # TODO can we get rid of freq or set to inf? I don't think it effects anything but still
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        photon.add_loss(1 - self.efficiency) # photon collection efficiency added

        # need to add loss for size of time-bin (atom may not have had time to decay)
        late_decay_prob = e**(-self.bin_width/self.state_lifetime) # probability photon not released after self.bin_width
        photon.add_loss(loss=late_decay_prob)

        # if self.timeline.quantum_manager.states[self.qstate_key].state[0] != np.complex128(0.7071067811865476+0j):
        #     raise ValueError('Unprepared state is getting to QFC.')

        self._receivers[0].get(photon, dst=dst)
        # self.excited_photon = photon # don't think this is necessary

    
    def initialize_cool_prep(self) -> int:
        if self.need_to_retrap:
            self.need_to_retrap = False
            added_delay = self.retrap_time
            if self.wavelength == 1389:
                self.atom_state = Yb1389States.P0
                self.efficiency = self.original_memory_efficiency
            elif self.wavelength == 556:
                self.atom_state = Yb556States.S0
                self.efficiency = self.original_memory_efficiency
        else:
            added_delay = 0

        # 3% loss due to depumping from 3P0 to 1S0
        if self.wavelength == 1389 and self.atom_state != Yb1389States.LOST:
            if self.get_generator().random() >= .975:
                self.atom_state = Yb1389States.LOST
                self.efficiency = 0
                log.logger.info("Atom " + str(self.name) + " lost in depumping.")
            else:
                # if not lost, atoms should already be in correct state here
                if self.wavelength == 1389:
                    self.atom_state = Yb1389States.P0
        if self.efficiency != 0:
            self.update_state(self._plus_state)
            log.logger.info('Atom ' + str(self.name) + ' succesfully prepared in |+>.')
        # else:
        #     raise ValueError('Efficiency shouldnt be zero in current trials.')

        total_time = self.initialize_time + self.cool_time + self.state_prep_time + added_delay
        return total_time
    
    def atom_transition(self) -> bool:
        # dict of decay states with a probability, wavelength tuple as the values
        if self.wavelength == 1389:
            if self.atom_state == Yb1389States.LOST:
                return None
            elif self.atom_state == Yb1389States.P0:
                if self.get_generator().random() <= self.P0_decay:
                    return 1389
                elif self.get_generator().random() <= (self.P0_decay + self.S0_decay):
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
        
    def measure(self, other_qkey) -> float:
        key = self.qstate_key
        keys = [key, other_qkey]
        qm = self.timeline.quantum_manager

        for k in keys:
            # print(str(qm.states[k].state))
            if len(qm.states[k].state) != 4: # if not entangled
                log.logger.warning('Incorrectly entangled state.')
                # qm.set([k], [1, 0]) # TODO do I want to be thoughtful about how I'm setting up the states?

        
        if self.owner.app.basis == "X":
            qm.run_circuit(_H_circuit, keys).keys()

        meas = qm.run_circuit(_meas_circuit, keys, self.get_generator().random())

        result = [meas[key], meas[other_qkey]]
        
        # for ideal fidelity we expect:
        #   psi+:
        #       1,Z
        #       0,X
        #   psi-:
        #       1,Z
        #       1,X

        return result
    
    def set_wavelength(self, wavelength: int):
        if wavelength == 1389:
            self.initialize_time = 51_400_000
            self.cool_time = 1_400_000_000
            self.clock_pulse_time = 5_000_000
            self.raman_half_pi_pulse_time = 300_000
            self.state_prep_time = self.clock_pulse_time + self.raman_half_pi_pulse_time
            self.excite_pulse_time = 16_000
            self.phase_flip_time = 700_000
            self.bin_gap = 2_100_000 # this is 2.8 microseconds separation minus 0.7microseconds raman pi pulse
            self.atom_state = Yb1389States.P0
            self.retrap_num = 128
            self.measurement_time = 37_510_000_000
            self.state_lifetime = 330_000 # THIS IS IMPORTANT: HOW LONG 3D1 decay on average lasts, thus with the excite pulse time is the bin width
            self.atom_lifetime = 10_000_000_000_000 # from Covey Paper TODO check with Michael
            self.lifetime_reload_time = 10_000_000_000_000
            self.bin_width = 520_000 # this is the size of the detection window
        elif wavelength == 556:
            self.initialize_time = 20_000_000
            self.cool_time = 1_400_000_000
            self.raman_half_pi_pulse_time = 850_000
            self.state_prep_time = self.raman_half_pi_pulse_time
            self.excite_pulse_time = 20_000
            self.phase_flip_time = 1_800_000
            self.bin_gap = 4_200_000 # this is 6 microseconds separation minus 1.8 microseconds raman pi pulse
            self.atom_state = Yb556States.S0
            self.measurement_time = 30_000_000_000
            self.state_lifetime = 870_000 # THIS IS IMPORTANT: HOW LONG 3P1? decay on average lasts, thus with excite pulse time is the bin width
            self.atom_lifetime = 40_000_000_000_000
            self.lifetime_reload_time = 40_000_000_000_000
            self.bin_width = 1_400_000 # TODO check if this matches P of still being in excited stated in 1389 case given 556 lifetime
        else:
            raise ValueError('Wavelength ' + str(wavelength) + ' is not supported for ' + self.name + '.')
        
        self.to_x_basis_time = self.raman_half_pi_pulse_time
        self.bin_separation = self.bin_gap + self.phase_flip_time + self.excite_pulse_time
        self.wavelength = wavelength

    def lose_atom(self):
        self.efficiency = 0
        qm = self.owner.timeline.quantum_manager
        if self.wavelength == 1389:
            if self.atom_state != Yb1389States.LOST:
                log.logger.warning(f'{self.name} atom lost through lifetime expiration!')
                self.atom_state = Yb1389States.LOST
                if len(qm.states[self.qstate_key].keys) == 1:
                    self.update_state(self._zero_ket)
                else: # entangled states
                    for key in qm.states[self.qstate_key].keys:
                        if key == self.qstate_key: # this memory
                            self.update_state(self._zero_ket)
                        else: # other memory
                            if self.psi_sign == -1: # psi-
                                qm.set([key], self._minus_state)
                            else: #psi+
                                qm.set([key], self._plus_state)
        elif self.wavelength == 556:
            if self.atom_state != Yb556States.LOST:
                log.logger.warning(f'{self.name} atom lost through lifetime expiration!')
                self.atom_state = Yb556States.LOST
                self.update_state(self._zero_ket)


# model for uW chip which includes a transmon coupled to a resonator as as an on-chip tranducer
class uW(Memory):

    _plus_state = [sqrt(1/2), sqrt(1/2)]
    _zero_ket = [1,0]

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int):
        
        super().__init__(name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength)

        self.wavelength = 30_000_000 # this is 10GHz                                # 1 wavelength
        self.attempts = 0                               
        self.psi_sign = None # 1 for psi+, -1 for psi-
        self.time_after_excitement = None

        #self.t1_coherence = 100_000_000
        self.coherence_time = 100_000_000 # this is t1 coherence I think                 # 2 coherence
        # self.t2_coherence = 100_000_000 commenting out because we don't use

        # initialization time                                                       # 3 init time
        self.initialize_time = 5*self.coherence_time # time to get everything into ground state (previously was 5*t1_coherence)
        # my source actually says 500ns but Xu said 5*self.coherence which happen to align?

        self.cool_time = 0

        # prep time
        self.ge_pi_pulse_time = 20_000 # time to drive from |g> -> |e>              # 4 
        self.ef_halfpi_pulse_time = 10_000 # TODO need to get verification from Xu. # 5
        self.state_prep_time = self.ge_pi_pulse_time + self.ef_halfpi_pulse_time

        self.excite_pulse_time = 0 # no concept of an excite pulse for uW system
        self.emission_pulse_time = 200_000 # time to drive decay from |f0> -> |g1>. # 6
        self.bin_width = self.emission_pulse_time # minimium bin width this device cooperates with # I just set to 200_000 - should change

        self.bin_gap = 0 # this is just the time we way to ensure full decay # i just set to zero, should change
        self.ef_pi_pulse_time = 20_000 # time to drive from |e> -> |f>              # 7
        self.bin_separation = self.bin_width + self.bin_gap + self.ef_pi_pulse_time # minimum separation needed between bins

        # for measurement
        self.ge_halfpi_pulse_time = 10_000 # TODO need to get verification from Xu.      # 8
        self.to_x_basis_time = self.ge_halfpi_pulse_time                                 
        self.measurement_time = 88_000 #12_000_000 was previously here, not sure why # 9
        self.measurement_fidelity = .992 # bookmarked source                             # 10

        self.output_wavelength = 1389 # wavelength we're going to transduce to.          # 11
        # this is the product of on-chip efficiency and fiber-chip coupling efficiency
        self.transduction_efficiency = 0.6                                               # 12
        self.chip_to_fiber_efficiency = 0.1  # chip to fiber coupling efficiency         # 13
        self.transducer_efficiency = self.transduction_efficiency * self.chip_to_fiber_efficiency
        # in paper, I will have one overall transducer efficiency we alter based on both previous two variables
        self.transducer_noise = 0.87                                                     # 14
    
    def initialize_cool_prep(self) -> int:
        self.update_state(self._plus_state)
        log.logger.info('Transmon ' + str(self.name) + ' succesfully prepared in |+>.')
        time = self.initialize_time + self.state_prep_time + self.cool_time
        return time # time to initialize and prep
    
    def noise_to_num(self) -> int:
        # num = round(self.transducer_noise) # should make a more probabilitistic sampling
        k = self.owner.get_generator().geometric(1/(self.transducer_noise + 1))
        num = k-1
        return num
    
    def transduce(self, photon: Photon) -> Photon:
        photon.wavelength = self.output_wavelength
        photon.add_loss(1 - self.transducer_efficiency)
        noise_num = self.noise_to_num()
        photon.transducer_noise_count = noise_num
        return photon

    def excite(self, dst="") -> None:

        self.time_after_excitement = self.owner.timeline.now() + self.bin_separation

        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time: # TODO can we initialize frequency as Inf?
            return

        uw_encoding = {'name': 'uw_time_bin'}
        photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name, encoding_type=uw_encoding, 
        quantum_state=self.qstate_key, use_qm=True) #TODO ADD A WAY TO POINT TOWARDS THE ACTUAL FOUR_VECTOR ENTANGLED STATE (FOR ATOM AND PHOTON)

        photon.timeline = None  # facilitate cross-process exchange of photons

        if self.frequency > 0: # TODO can we get rid of freq or set to inf? I don't think it effects anything but still
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        photon = self.transduce(photon) # push through transducer

        decohere_prob = (1 - e**(-self.bin_separation/self.coherence_time)) # prob decoheres during generation
        if self.owner.get_generator().random() < decohere_prob: # transmon decohered
            photon.only_early = True
            self.update_state(self._zero_ket) # |e> -> |g>

        photon.is_null = True
        self._receivers[0].get(photon, dst=dst)
        

    def measure(self, other_qkey) -> float:
        key = self.qstate_key
        keys = [key, other_qkey]
        qm = self.timeline.quantum_manager

        for k in keys:
            # print(str(qm.states[k].state))
            if len(qm.states[k].state) != 4: # if not entangled
                log.logger.warning('Incorrectly entangled state.')
                # qm.set([k], [1, 0]) # TODO do I want to be thoughtful about how I'm setting up the states?

        
        if self.owner.app.basis == "X":
            qm.run_circuit(_H_circuit, keys).keys()

        meas = qm.run_circuit(_meas_circuit, keys, self.get_generator().random())

        result = [meas[key], meas[other_qkey]]
        
        # for ideal fidelity we expect:
        #   psi+:
        #       1,Z
        #       0,X
        #   psi-:
        #       1,Z
        #       1,X

        return result

