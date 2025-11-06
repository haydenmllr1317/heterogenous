"""Models for simulating bell state measurement.

This module defines a template bell state measurement (BSM) class,
as well as implementations for polarization, time bin, and memory encoding schemes.
Also defined is a function to automatically construct a BSM of a specified type.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from sequence.kernel.quantum_manager import QuantumManager
    from sequence.kernel.quantum_state import State
    from sequence.kernel.timeline import Timeline

from numpy import outer, add, zeros, array_equal

from sequence.components.circuit import Circuit
from detector import Detector
from photon import Photon
from sequence.kernel.entity import Entity
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.quantum_manager import KET_STATE_FORMALISM, DENSITY_MATRIX_FORMALISM
from encoding import *
from sequence.utils import log
from sequence.components.bsm import _set_state_with_fidelity
from copy import copy
from sequence.components.bsm import BSM

class HetTimeBinBSM(BSM):
    """Class modeling a time bin BSM device.

    Recieves time-bin photons and passes them on to detectors. When detectors have been triggered
    at time-bin separated times, it notifies BSMNode and heralds memory entanglement.

    Attributes:
        name (str): label for BSM instance
        timeline (Timeline): timeline for simulation
        detectors (List[Detector]): list of attached photon detection devices
        phase_error (float): phase error applied to polarization qubits (unused)
        encoding (str): 'time_bin', used in 'BSM' class to ensure recieved
            photon is of the same encoding type
        trigger_times (List[int]): time-ordered list of recent times detectors clicked
        signal_values (List[bool]): time-ordered list of booleans of whether recently arrived photons
            that caused detector clicks where signals or not.
        detector_hits (List[int]): time-ordered list of numbers of recently triggered detectors.
        
        
        ######### NOT USING THE REST OF THESE FOR NOW
        last_res (List[Int]): pair of ints, initially set to [-1,-1], where the
            first int is the time of the last time 'trigger' was called and the
            second int is the detector (0 or 1) that caused said trigger
        early_early (int): total count of photon pairs the device measured as
            both being early
        early_late (int): total count of photon pairs the device measured as
            photon1 being early and photon2 being late
        late_early (int): total count of photon pairs the device measured as
            photon2 being late and photon2 being early
        late_late (int): total count of photon pairs the device measured as
            both being late
        desired_state (bool): true if photons are |early,late> or |late,early>,
            else false
        trigger_count (int): count how many times trigger function was called
        appropriate_time_photon_count (int): counts how many photons cause a
            trigger at roughly the bin_separation time from the previous photon
            arrival. this should only be the late photons in an early+late pair
        approved_state_invalid_time_photon_count (int): counts how many photons
            that come from an early+late pair (valid) arrive at an invalid time,
            meaning not a bin_separation time away from the previous photon.
            this should only be the early photons in said pairs.
        invalid_state_photon_count (int): counts how many photons that come from
            an invalid pair (late+late or early+early) arrive at an invalid
            time. this should be half of them, as the detector can register
            one photon at a time and they will arrive at the same time and same
            detector (by HOM effect).

    """

    _meas_circuit = Circuit(1)
    _meas_circuit.measure(0)

    def __init__(self, name, timeline, phase_error=0, detectors=None):
        """Constructor for the time bin BSM class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization qubits (unused) (default 0).
            detectors (List[Dict]): list of parameters for attached detectors,
                in dictionary format (must be of length 2) (default None).
        """

        if detectors is None:
            detectors = [{}, {}]

        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = 'het_time_bin'

        self.last_res = [-1, -1]
        self.early_early = 0 # currently not using
        self.early_late = 0 # currently not using
        self.late_early = 0 # currently not using
        self.late_late = 0 # currently not using
        self.desired_state = None # currently not using
        self.trigger_count = 0
        self.appropriate_time_photon_count = 0
        self.approved_state_invalid_time_photon_count = 0
        self.invalid_state_photon_count = 0

        self.time_bin_separation = None # time separating our bins
        self.bin_width = None # size of our time bins
        
        
        # for our BSM setup...
        assert len(self.detectors) == 2

    def get(self, photon, **kwargs):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        log.logger.debug(self.name + " recieved 'photon' quantum information.")

        qm = self.timeline.quantum_manager
        key = photon.quantum_state # key pointing to ket state of photon
        photon_odds = self.get_generator().random()
        measurement = qm.run_circuit(self._meas_circuit, [key], self.get_generator().random())[key]

        late_time = self.timeline.now() + self.time_bin_separation # time of late photon

        detector_num_signal = self.get_generator().choice([0,1]) # detector where signal photon goes
        detector_num_noise = self.get_generator().choice([0,1]) # detector where noise photon goes

        # add noise if needed
        if photon.mode_count == 0:
            raise ValueError(f"Shouldn't have zero photons in {photon.name} mode.")
        elif photon.mode_count == 1:
            pass
        elif photon.mode_count > 1:
            noise_time = self.owner.timeline.now() + round(self.get_generator().random() * self.bin_width) # where within the detection window noise is added
            noise_get_args = {'signal': False, 'qkey': photon.quantum_state}
            process_noise = Process(self.detectors[detector_num_noise], "get", [], noise_get_args)
            event_noise = Event(noise_time, process_noise)
            self.timeline.schedule(event_noise)


        # add signal
        if measurement == 0: # early photon
            if photon_odds >= photon.loss: # photon survives the QFC
                get_args = {'signal': True, 'qkey': photon.quantum_state}
                self.detectors[detector_num_signal].get(**get_args)
                log.logger.info(f'{self.name} sent signal photon to detector {detector_num_signal} at early time bin.')
        else: # late photon
            if photon_odds >= photon.loss: # photon survives QFC
                get_args = {'signal': True, 'qkey': photon.quantum_state}
                process = Process(self.detectors[detector_num_signal], "get", [], get_args)
                event = Event(late_time, process)
                self.timeline.schedule(event)
                log.logger.info(f'{self.name} sent signal photon to detector {detector_num_signal} at late time bin.')
                

    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """

        This class is called in the Detector modules to indicate a detector
        was clicked. It consumes:

        detector(Detector) - what detector click comes from
        info (Dict[str, Any]) - contains time of click and possibly the quantum_state key
            of the "real" (not noise) photon that triggered the detector.

        """

        # new trigger function for the millionth time
        self.trigger_count += 1

        detector_num = self.detectors.index(detector)
        time = info["time"]
        try:
            signal = info["signal"] # is True if a signal photon caused detector trigger, False if QFC noise did
        except Exception:
            signal = False # detector dark count
        try:
            key = info['qkey'] # as long as NOT a detector dark count, will have a quantum key from photon
        except Exception:
            key = None # detector dark count

        info = {'info_type': 'BSM_res', 'res': detector_num, 'time': time, 'signal': signal, 'qkey': key}

        self.notify(info)