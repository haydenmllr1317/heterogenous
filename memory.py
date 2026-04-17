"""Models for simuulation of memory components in a heterogenous quantum network. # NOTE HM done

This model builds on SeQUeNCe's memory module, but adds an altered memory array class (HetMemoryArray), and two new memory class (Yb and uW).
HetMemoryArray inhereits from MemoryArray with all the same functionality except enabling alternative types of memories.
NOTE: If MemoryArray would allow component_templates or memo_type inputs, we wouldn't need a separate class for HetMemoryArray.
Yb and uW both inherit from Memory, but have different parameters and methods to reflect their physical differences.

"""

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline
from photon import HetPhoton
from sequence.kernel.entity import Entity
from sequence.utils import log
from enum import Enum, auto
from sequence.components.circuit import Circuit
from sequence.components.memory import Memory, MemoryArray
from math import sqrt, e
from sequence.kernel.quantum_manager import QuantumManager
from sequence.constants import BELL_DIAGONAL_STATE_FORMALISM

_meas_circuit = Circuit(2)
_meas_circuit.measure(0)
_meas_circuit.measure(1)
_H_circuit = Circuit(2)
_H_circuit.h(0)
_H_circuit.h(1)

_photon_meas_circuit = Circuit(1)
_photon_meas_circuit.measure(0)


class HetMemoryArray(MemoryArray):
    """Aggregator for Memory objects in heterogenous network. # NOTE HM done

    Equivalent to an array of single atom memories.
    Also equivalent to MemoryArray except can be initialized with new memory types.
    The MemoryArray can be accessed as a list to get individual memories.

    Attributes:
        name (str): label for memory array instance.
        timeline (Timeline): timeline for simulation.
        memories (List[Memory]): list of all memories.
    """

    def __init__(self, name: str, timeline: "Timeline", memory_type: str, num_memories=10, 
                 fidelity=0.85, frequency=80e6, efficiency=1,coherence_time=-1, wavelength=500,
                 decoherence_errors: List[float] = None, cutoff_ratio = 1, cutoff_flag: bool = True):
        """Constructor for the Heterogenous Memory Array class.

        Args:
            name (str): name of the memory array instance.
            timeline (Timeline): simulation timeline.
            memory_type (str): type of memories in the array (should be either 'Yb' or 'uW').
            num_memories (int): number of memories in the array (default 10).
            fidelity (float): fidelity of memories (default 0.85).
            frequency (float): maximum frequency of excitation for memories (default 80e6).
            efficiency (float): efficiency of memories (default 1).
            coherence_time (float): average time (in s) that memory state is valid (default -1 -> inf).
            wavelength (int): wavelength (in nm) of photons emitted by memories (default 500).
            decoherence_errors (list[int]): pauli decoherence errors. Passed to memory object.
            cutoff_ratio (float): the ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
            cutoff_flag (bool): Flag to enable or disable expiry events
        """

        Entity.__init__(self, name, timeline)
        self.memories: list[Memory] = []
        self.memory_name_to_index = {}
        self.memo_type = memory_type # TODO check if this needs to be saved as a class feature 

        if decoherence_errors is not None:
            assert QuantumManager.get_active_formalism() == BELL_DIAGONAL_STATE_FORMALISM, (
                "Decoherence errors can only be set when formalism is Bell Diagonal")

        # Set the default pauli errors if BDS formalism
        if QuantumManager.get_active_formalism() == BELL_DIAGONAL_STATE_FORMALISM and decoherence_errors is None:
            decoherence_errors = [1/3, 1/3, 1/3]

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

# class for electronic states of Yb atoms in Yb memory class for 1389nm emission
# TODO check if we even need this anymore/give some justification
class Yb1389States(Enum):
    S0 = auto()     # for 1S0 state
    P0 = auto()     # for 3P0 state
    LOST = auto()   # for atom fallen out of trap


# class for electronic states of Yb atoms in Yb memory class for 1389nm emission
# TODO check if we even need this anymore/give some justification
class Yb556States(Enum):
    S0 = auto()     # for 1S0 state
    LOST = auto()   # for atom fallen out of trap


class Yb(Memory):
    """ Yb memory class.     #NOTE HM done except for excite, measure, and set_wavelength methods, which are still being worked on

    This class models a single Yb atom memory, where the quantum state in stored in the nuclear spin of a single atom.
    This class is follows Li et al.'s work on quantum networking with an Yb-171 array (https://arxiv.org/abs/2502.17406).
    The methods and parameterization are according to the paper, conversations with Dr. Michael Bishof of Argonne National Lab, and other literature on Yb-171.

    I will count these parameters and the EG step they occur in simply for keeping track in the paper.

    Attributes:
        name (str): name of the memory instance.
        timeline (Timeline): simulation timeline.
        fidelity (float): initial fidelity of memory.
        frequency (float): maximum frequency of excitation for memory.
        efficiency (float): efficiency of memories.                                                                 #1
        coherence_time (float): average time (in s) that memory state is valid.                                     #2
        decoherence_rate (float): rate of decoherence to implement time dependent decoherence.
        wavelength (int): wavelength (in nm) of photons emitted by memories.                                        #3
        original_memory_efficiency (float): initial efficiency of memories before atom loss. # TODO Do we still need this? is it duplicitous with atom state?
        time_after_excitement (int): simulation time right after excitement, for use in decoherence calculations.
        atom_state (Yb1389States or Yb556States): Enum for electronic state of Yb atom                              #4
        state_lifetime (int): lifetime of the excited state of Yb, for calculatting emission prob.                  #5
        S0_decay (float): branching proportion for decay from 3D1 to 1S0 state                                      #6
        P0_decay (float): branching proportion for decay from 3D1 to 3P0 state                                      #7
        LOST_decay (float): branching proportion for decay from 3D1 to LOST state                                   #8
        atom_lifetime (int): lifetime of the atom in the trap, for calculating atom loss.                           #9
        lifetime_reload_time (int): time after which we reload atoms to counter loss from atom_lifetime             #10
        psi_sign (int): notation for sign of rour Bell state. 1 for psi+, -1 for psi-
        attempts (int): num of EG attempts since last atom retrap
        retrup_num (int): number of EG attempts before we need to reload atom array                                 #11                   
        need_to_retrap (bool): flag to indicate it's time for the atom to be retrapped
        retrap_time (int): time it takes to retrap an atom (reload time of the array)                               #12 (STEP 1/6 of EG)
        initialize_time (int): time to prepare Yb in ground state (each EG attempt)                                 #13 (STEP 2/6 of EG)
        cool_time (int): time to cool Yb after initialization (each EG attempt)                                     #14 (STEP 3/6 of EG)
        clock_pulse_time (int): time to promote Yb to clock state (where qubit is encoded)                          #15 (STEP 4(a)/6 of EG)
        raman_half_pi_pulse_time (int): time for pulse to create |+> superposition state                            #16 (STEP 4(b)/6 of EG)
        state_prep_time (int): time for state preparation (sum of previous two attributes)
        excite_pulse_time (int): time to excite Yb (for photon emission in EG)                                      #17 (STEP 5(a)/6 of EG)
        bin_width (int): width of time bin for photon detection in EG                                               #18 (STEP 5(b)/6 of EG)
        bin_gap (int): gap between end of first time bin and beginning of pulses for second time bin in EG          #19 (STEP 5(c)/6 of EG)
        phase_flip_time (int): time to apply phase flip gate on qubit state                                         #20 (STEP 5(d)/6 of EG)
        bin_separation (int): time between the two time bins in EG (sum of prev. 3 attributes)
        to_x_basis_time (int): time to rotate to X basis, just raman_half_pi_pulse_time here
        measurement_time (int): time to measure Yb state in Z basis                                                 #21 (STEP 6/6 of EG)
        measurement_fidelity (float): readout fidelity for Z basis measurement                                      #22
        CX_fidelity (float): fidelity for CX gate (used in entanglement swapping)                                   #23
        atom_bsm_time (int): time to perform Bell state measurement on two atoms (used in entanglement swapping)    #24

    """

    # self explanatory kets:
    _plus_state = [sqrt(1/2), sqrt(1/2)]
    _minus_state = [sqrt(1/2), -sqrt(1/2)]
    _zero_ket = [1,0]

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int):
        
        """ Constructor for the Yb class.

        Args:
            name (str): name of the memory instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): initial fidelity of memory.
            frequency (float): maximum frequency of excitation for memory.
            efficiency (float): efficiency of memories.
            coherence_time (float): average time (in s) that memory state is valid.
            decoherence_rate (float): rate of decoherence to implement time dependent decoherence.
            wavelength (int): wavelength (in nm) of photons emitted by memories.
        """
        
        super().__init__(name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength)

        # GENERAL PARAMETERS
        self.original_memory_efficiency = self.efficiency
        self.time_after_excitement = None
        self.atom_state = None
        self.state_lifetime = None
        self.S0_decay = 0.354     ###0.133 
        self.P0_decay = 0.637     ###0.863
        self.LOST_decay = 0.009   ###0.003
        self.atom_lifetime = None
        self.lifetime_reload_time = None
        self.psi_sign = None # 1 for psi+, -1 for psi- # TODO decide whether to stick with this or only have psi+
        self.attempts = 0   # TODO, can we fold attempts from node and form memory into just one variable?
        self.retrap_num = None
        self.need_to_retrap = False

        # ENTANGLEMENT GENERATION PARAMETERS PER STEP

        #### STEP 1: RESET
        self.retrap_time = 500_000_000_000

        #### STEP 2: INITIALIZATION
        self.initialize_time = None

        #### STEP 3: COOLING
        self.cool_time = None

        #### STEP 4: PREPARATION
        self.clock_pulse_time = None
        self.raman_half_pi_pulse_time = None
        self.state_prep_time = None

        ##### STEP 5: GENERATION
        self.excite_pulse_time = None
        self.bin_width = None
        self.bin_gap = None
        self.phase_flip_time = None
        self.bin_separation = None
        
        #### STEP 6: MEASUREMENT
        self.to_x_basis_time = None
        self.measurement_time = None
        self.measurement_fidelity = 0.995 # NOTE need to add # TODO change in set_wavelength??
    
        # SWAPPING PARAMETERS
        self.CX_fidelity = None # TODO what is 2-qubit gate fidelity? (0.997 is Infleqtion's result, 0.995 might be good default)
        self.atom_bsm_time = None # TODO how long does CX + Hadamard gate take? Also, do I even use this??

    def excite(self, dst="") -> None:
        """ Method to excite Yb atom for photon emission during entanglement generation.

        Called during entanglement generation (by HetEGA) to excite Yb atom and create and sent photon to destination.

        Args:
            dst (str): destination for emitted photon (default "").

        Side Effects:
            Calls atom_transition() which updates atom_state and efficiency.

        
        
        """

        self.time_after_excitement = self.owner.timeline.now() + self.bin_separation # used for decoherence during round trip
        
        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time:
            return
        
        # excite the atom, resulting in atom_state and efficiency changes, and returning the wavelength for our photon
        wavelength = self.atom_transition()

        # log if wrong transition or atom lost
        if wavelength != self.wavelength:
            log.logger.info('Photon with unideal wavelength of ' + str(wavelength) + ' emmited (wanted ' + str(self.wavelength) + ').')


        # yb_encoding = {'name': 'yb_time_bin', 'bin_separation': self.bin_separation, 'raw_fidelity': 1.0}
        yb_encoding = {'name': 'yb_time_bin', 'keep_photon': True}
        photon = HetPhoton("", self.timeline, wavelength=wavelength, location=self.name, encoding_type=yb_encoding, 
        quantum_state=self.qstate_key, use_qm=True) #TODO ADD A WAY TO POINT TOWARDS THE ACTUAL FOUR_VECTOR ENTANGLED STATE (FOR ATOM AND PHOTON)
        # keep track of memory initialization time
        # self.generation_time = self.timeline.now() # commented this out cuz I don't think we need
        # self.last_update_time = self.timeline.now() # commented this out cuz don't think we need

        photon.timeline = None  # facilitate cross-process exchange of photons
        photon.is_null = True

        # if photon.loss != 0:
        #     raise ValueError(f'{photon.name} just created, should have zero loss, not {photon.loss}.')

        # set next_excite_time
        if self.frequency > 0:
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
        """ Method to initialize, cool, and prepare Yb for entanglement generation.

        Called during entanglement generation (by HetEGA) to conduct intialization, cooling, and preparation steps.

        Returns:
            total_time (int): total time initialization, cooling, and preparation took.

        Side Effects:
            Updates atom state and memory efficiency according to branching ratios for initialization.
        """

        # RESET
        if self.need_to_retrap:
            self.need_to_retrap = False
            added_delay = self.retrap_time
            if self.wavelength == 1389:     # reset state and efficiency
                self.atom_state = Yb1389States.P0
                self.efficiency = self.original_memory_efficiency
            elif self.wavelength == 556:    # reset state and efficiency
                self.atom_state = Yb556States.S0
                self.efficiency = self.original_memory_efficiency
        else:
            added_delay = 0

        # INITIALIZATION
        if self.wavelength == 1389 and self.atom_state != Yb1389States.LOST:
            if self.get_generator().random() >= .975: # ~3% loss due to depumping from 3P0 to 1S0
                self.atom_state = Yb1389States.LOST
                self.efficiency = 0
                log.logger.info("Atom " + str(self.name) + " lost in depumping.")
            else:
                # if not lost, atoms should already be in correct state here
                if self.wavelength == 1389:
                    self.atom_state = Yb1389States.P0

        # PREPARATION
        if self.efficiency != 0:
            self.update_state(self._plus_state)
            log.logger.info('Atom ' + str(self.name) + ' succesfully prepared in |+>.')

        # ADD COOLING TIME
        total_time = self.initialize_time + self.cool_time + self.state_prep_time + added_delay
        return total_time
    
    def atom_transition(self) -> bool:
        """ Method to transition state of Yb atom during excitation step of entanglement generation.

        Called by excite() method during entanglement generation to transition state of Yb atom according to branching ratios for decay from excited state.

        Returns:
            wavelength (int): wavelength of emitted photon, or 999 if transition was wrong (but atom survive), or None if atom lost.

        Side Effects:
            Updates atom state and memory efficiency according to branching ratios for decay from excited state.
        """
        
        if self.wavelength == 1389:
            if self.atom_state == Yb1389States.LOST:
                return None
            elif self.atom_state == Yb1389States.P0:
                if self.get_generator().random() <= self.P0_decay:                          # 3P0 transition (correct, Yb emits 1389nm photon)
                    return 1389
                elif self.get_generator().random() <= (self.P0_decay + self.S0_decay):      # 3P1 transition (incorrect, but Yb survives)
                    self.atom_state = Yb1389States.S0
                    return 999
                else:                                                                       # 3P2 transition causes Yb to fall out of trap
                    log.logger.info(f'Atom {self.name} lost in transition.')
                    self.atom_state = Yb1389States.LOST
                    self.efficiency = 0
                    return 999
            else:
                raise ValueError(f'Prior to transition, atom is incorrectly in {self.atom_state}.' )
        elif self.wavelength == 556:
            if self.atom_state == Yb556States.LOST:
                return None
            elif self.atom_state == Yb556States.S0:                                         # correct transition, Yb emits 556nm photon
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
    
    def transduce(self, photon: HetPhoton) -> HetPhoton:
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

        uw_encoding = {'name': 'uw_time_bin', 'keep_photon': True}
        photon = HetPhoton("", self.timeline, wavelength=self.wavelength, location=self.name, encoding_type=uw_encoding, 
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

