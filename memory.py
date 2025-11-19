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
import numpy as np

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
# from generation import EntanglementGenerationTimeBin as EGTB
from enum import Enum, auto
from sequence.components.circuit import Circuit
from sequence.components.bsm import _set_state_with_fidelity
from sequence.components.memory import Memory
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




class Yb1389States(Enum):
    S0 = float(-1) # for 1S0 state

    # the values of these three are their branching ratios
    # NOTE CHANGING THESE
    # P0 = 0.637 # for 3P0 state
    # P1 = 0.354 # for 3P1 state
    # P2 = 0.009 # for 3P2 state

    P0 = 1.0 # for 3P0 state
    P1 = 0.0 # for 3P1 state 
    P2 = 0.0 # for 3P2 state
    
    # arbitrary value now
    LOST = float(-2) # for atom fallen out of trap

class Yb556States(Enum):
    S0 = auto() # for 1S0 state
    LOST = auto() # for atom fallen out of trap


class Yb(Memory):

    _plus_state = [sqrt(1/2), sqrt(1/2)]

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int, decoherence_errors: List[float] = None, cutoff_ratio: float = 1):
        
        super().__init__(name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength, decoherence_errors, cutoff_ratio)

        self.original_memory_efficiency = self.efficiency

        self.counter = 0

        self.retrap_time = 500_000_000_000
        self.psi_sign = None # 1 for psi+, -1 for psi-
        self.attempts = 0
        self.need_to_retrap = False

        self.initialize_time = None
        self.cool_time = None
        self.clock_pulse_time = None
        self.raman_half_pi_pulse_time = None
        self.state_prep_time = None
        self.excite_pulse_time = None
        self.phase_flip_time = None
        self.bin_gap = None
        self.atom_state = None
        self.retrap_num = None
        self.readout_time = None
        self.state_lifetime = None
        self.atom_lifetime = None
        self.lifetime_reload_time = None
        self.bin_width = None # detection window

        self.bin_separation = None



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
        else:
            raise ValueError("Invalid encoding type {} specified for memory.exite()".format(encoding_type))

        photon.timeline = None  # facilitate cross-process exchange of photons
        # photon.is_null = True # NOTE I changed this cuz I don't think we need

        # if photon.loss != 0:
        #     raise ValueError(f'{photon.name} just created, should have zero loss, not {photon.loss}.')

        if self.frequency > 0:
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        photon.add_loss(1 - self.efficiency)

        # need to add loss for size of time-bin (atom may not have had time to decay)
        # NOTE COMMENTING THIS OUT FOR bug CHECKING
        # late_decay_prob = e**(-self.bin_width/self.state_lifetime) # probability photon not released after self.bin_width
        # photon.add_loss(loss=late_decay_prob)

        if self.timeline.quantum_manager.states[self.qstate_key].state[0] != np.complex128(0.7071067811865476+0j):
            raise ValueError('Unprepared state is getting to QFC.')

        self._receivers[0].get(photon, dst=dst)
        self.excited_photon = photon

    
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
        # NOTE COMMENTED THIS OUT FOR TRIALS
        # if self.atom_state != Yb1389States.LOST and self.wavelength == 1389:
        #     if self.get_generator().random() >= .975:
        #         self.atom_state = Yb1389States.LOST
        #         self.efficiency = 0
        #         log.logger.info("Atom " + str(self.name) + " lost in depumping.")
        #     else:
        #         # if not lost, atoms should already be in correct state here
        #         if self.wavelength == 1389:
        #             self.atom_state = Yb1389States.P0
        if self.efficiency != 0:
            self.update_state(self._plus_state)
            log.logger.info('Atom ' + str(self.name) + ' succesfully prepared in |+>.')
        else:
            raise ValueError('Efficiency shouldnt be zero in current trials.')

        total_time = self.initialize_time + self.cool_time + self.state_prep_time + added_delay
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
        
    def measure(self, other_qkey) -> float:
        # ideally this process is supressing the measured qubits state and forcing the key to point towards
        # the others'

        key = self.qstate_key
        # key1 = self.timeline.get_entity_by_name(self.entangled_memory['node_id'] + '.MemoryArray[0]').qstate_key
        keys = [key, other_qkey]

        # print(self.timeline.quantum_manager.states[0].state)
        # if self.timeline.quantum_manager.states[0].state != self.timeline.quantum_manager.states[1].state:
        #     raise ValueError('soemthing weird')
        qm = self.timeline.quantum_manager

        for k in keys:
            # print(str(qm.states[k].state))
            if len(qm.states[k].state) != 4: # if not entangled
                log.logger.warning('Incorrectly entangled state.')
                # qm.set([k], [1, 0])

        
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
            self.readout_time = 37_510_000_000
            # self.qchannel_time_correction = 9_000 # this is to make bin_separation divisible by qchannel frequency
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
            self.readout_time = 30_000_000_000
            self.state_lifetime = 870_000 # THIS IS IMPORTANT: HOW LONG 3P1? decay on average lasts, thus with excite pulse time is the bin width
            self.atom_lifetime = 40_000_000_000_000
            self.lifetime_reload_time = 40_000_000_000_000
            self.bin_width = 1_400_000 # TODO check if this matches P of still being in excited stated in 1389 case given 556 lifetime
        else:
            raise ValueError('Wavelength ' + str(wavelength) + ' is not supported for ' + self.name + '.')
        
        self.bin_separation = self.bin_gap + self.phase_flip_time + self.excite_pulse_time
        self.wavelength = wavelength

    def lose_atom(self):
        self.efficiency = 0
        if self.wavelength == 1389:
            if self.atom_state != Yb1389States.LOST:
                log.logger.warning(f'{self.name} atom lost through lifetime expiration!')
                self.atom_state = Yb1389States.LOST
        elif self.wavelength == 556:
            if self.atom_state != Yb556States.LOST:
                log.logger.warning(f'{self.name} atom lost through lifetime expiration!')
                self.atom_state = Yb556States.LOST


    
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


