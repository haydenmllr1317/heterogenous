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

        # super from Entity class
        self.name: str                  = name
        self.timeline: Timeline         = timeline
        self.owner: "Entity" | None     = None
        self._observers: list[Any]      = []
        self._receivers: list["Entity"] = []
        timeline.add_entity(self)

        # super from BSM class
        self.encoding = "het_time_bin"
        self.phase_error = phase_error

        self.detectors = []
        if detectors is not None:
            for i, d in enumerate(detectors):
                if d is not None:
                    detector = Detector(f"{self.name}_{i}", timeline, **d)
                    detector.attach(self)
                    detector.owner = self
                else:
                    detector = None
                self.detectors.append(detector)

        self.bin_separation = 0 # time separating our bins
        self.bin_width = 0 # size of our time bins

        self.measurement = None
        
        
        # for our BSM setup...
        assert len(self.detectors) == 2

    def get(self, photon):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        log.logger.debug(self.name + " recieved 'photon' quantum information.")

        qm = self.timeline.quantum_manager
        key = photon.quantum_state # key pointing to ket state of photon
        measurement = qm.run_circuit(self._meas_circuit, [key], self.get_generator().random())[key] # 0 for early, 1 for late

<<<<<<< HEAD
            p0_odds = self.get_generator().random()
            p1_odds = self.get_generator().random()

            if (not meas0) and (not meas1):
                self.early_early += 1
                self.desired_state = False
                # HOM interference gives same detector
                detector_num = self.get_generator().choice([0,1])
                if p0_odds > p0.loss:
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p0')

                if p1_odds > p1.loss:
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p1')
            
            elif (not meas0) and meas1:
                self.early_late += 1
                detector_num1 = self.get_generator().choice([0,1])
                detector_num2 = self.get_generator().choice([0,1])

                if p0_odds > p0.loss and p1_odds > p1.loss:
                    self.desired_state = True
                    if detector_num1 == detector_num2:
                        _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"],
                                                self.get_generator(), qm)
                        # if self.timeline.quantum_manager.states[0].state[0] != 0:
                        #     print(self.timeline.quantum_manager.states[0].state[0])
                    else:
                        _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"],
                                                self.get_generator(), qm)
                else:
                    self.desired_state = False

                if p0_odds > p0.loss:
                    self.detectors[detector_num1].get()
                else:
                    log.logger.info(f'{self.name} lost photon p0')
                if p1_odds > p1.loss:
                    process = Process(self.detectors[detector_num2], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p1')

            elif meas0 and (not meas1):
                self.late_early += 1
                detector_num1 = self.get_generator().choice([0,1])
                detector_num2 = self.get_generator().choice([0,1])

                if p0_odds > p0.loss and p1_odds > p1.loss:
                    self.desired_state = True
                    if detector_num1 == detector_num2:
                        _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"],
                        self.get_generator(), qm)
                    else:
                        _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"],
                        self.get_generator(), qm)
                else:
                    self.desired_state = False

                if p0_odds > p0.loss:
                    process = Process(self.detectors[detector_num1], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p0')
                if p1_odds > p1.loss:
                    self.detectors[detector_num2].get()
                else:
                    log.logger.info(f'{self.name} lost photon p1')

            elif meas0 and meas1:
                self.late_late +=1
                self.desired_state = False
                # HOM interference gives same detector
                detector_num = self.get_generator().choice([0,1])
                if p0_odds > p0.loss:
                    process = Process(self.detectors[detector_num], "get", [])
                    event = Event(int(round(late_time)), process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p0')
                if p1_odds > p1.loss:
                    process = Process(self.detectors[detector_num], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p1')
=======
        detector_num_signal = self.get_generator().choice([0,1]) # detector where signal photon goes
        detector_num_noise = self.get_generator().choice([0,1]) # detector where noise photon goes

        self.measurement = measurement # adding this for tracking weird noise issues

        # add QFC noise if needed
        if photon.qfc_noise_count == 0: # only signal in mode
            pass
        elif photon.qfc_noise_count == 1: # noise photon in mode
            self.owner.noise_to_detector += 1
            noise_bin = int(self.get_generator().choice([0,1])) # 0 for early, 1 for late
            noise_time = self.owner.timeline.now() + (noise_bin*self.bin_separation) + round(self.get_generator().random() * self.bin_width) # where within appropriate detection window noise is added
            noise_get_args = {'photon_type': 0} # noisy photon
            process_noise = Process(self.detectors[detector_num_noise], "get", [], noise_get_args)
            event_noise = Event(noise_time, process_noise)
            self.timeline.schedule(event_noise)
        else:
            raise ValueError('We only consider up to 1 QFC noise photon.')

        # add transducer noise
        for i in range(photon.transducer_noise_count):
            photon_odds = self.get_generator().random()
            if photon_odds >= photon.loss: # photon survives to detector
                self.owner.noise_to_detector += 1
                noise_bin = int(self.get_generator().choice([0,1]))
                noise_time = self.owner.timeline.now() + (noise_bin*self.bin_separation) + round(self.get_generator().random() * self.bin_width) # where within appropriate detection window noise is added
                noise_get_args = {'photon_type': 0} # noisy photon
                process_noise = Process(self.detectors[detector_num_noise], "get", [], noise_get_args)
                event_noise = Event(noise_time, process_noise)
                self.timeline.schedule(event_noise)

        # add signal
        if photon.contains_signal: # photon object is not solely noise
            photon_odds = self.get_generator().random()
            if (photon_odds >= photon.loss): # now: photon must survive to detector
                if not photon.only_early: # no decoherence during generaiton
                    signal_get_args = {'photon_type': 1} # signal photon
                    signal_time = self.timeline.now() + (measurement * self.bin_separation) + round(self.get_generator().random() * self.bin_width) # where within appropriate detrection window noise is added
                    process_signal = Process(self.detectors[detector_num_signal], "get", [], signal_get_args)
                    event_signal = Event(signal_time, process_signal)
                    self.timeline.schedule(event_signal)
                else: # photon decohered during generation, only early pulse
                    if measurement == 0:
                        signal_get_args = {'photon_type': 3} # partial signal photon
                        signal_time = self.timeline.now() + (measurement * self.bin_separation) + round(self.get_generator().random() * self.bin_width) # where within appropriate detrection window noise is added
                        process_signal = Process(self.detectors[detector_num_signal], "get", [], signal_get_args)
                        event_signal = Event(signal_time, process_signal)
                        self.timeline.schedule(event_signal)
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec


                

    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """

        This class is called in the Detector modules to indicate a detector
        was clicked. It consumes:

        detector(Detector) - what detector click comes from
        info (Dict[str, Any]) - contains time of click and possibly the quantum_state key
            of the "real" (not noise) photon that triggered the detector.

        """

        detector_num = self.detectors.index(detector)
        time = info["time"]
        try:
            click_type = info["photon_type"] # 0 if noisy photon, 1 if signal photon
        except Exception:
            click_type = 2 # detector dark count

        if click_type == 0:
            self.owner.trigger_sent += 1

<<<<<<< HEAD
        # check if valid time
        # if round((time - self.last_res[0]) / self.encoding["bin_separation"]) == 1:
        if abs(((time - self.last_res[0]) / self.encoding["bin_separation"]) - 1.0) < 0.0001: # I SHOULD CHANGE THIS TO FACTOR IN RESOLUTiON IN A SANE WAY
            print(abs(((time - self.last_res[0]) / self.encoding["bin_separation"]) - 1.0))
            if (not self.desired_state):
                # an 'undesired state' is one that is either |early,early>
                #   or |late,late>. thus the photons' timing should be
                #   negligible compared to the bin_separation
                log.logger.error('An undesired state had correct separation.') # CHANGED FROM ERROR TO INFO
            self.appropriate_time_photon_count += 1
            # Psi+
            if detector_num == self.last_res[1]:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 0, 'time': time}
                self.notify(info)
            # Psi-
            else:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 1, 'time': time}
                self.notify(info)
        elif self.desired_state:
            # an approved states is either |early,late> or |late,early>. the
            # print(str(abs(((time - self.last_res[0]) / self.encoding["bin_separation"]) - 1.0)))
            #   early photon should always have invalid time, but late one
            #   shouldn't. the counter below should equal
            #   self.appropriately_timed_photon_count
            self.approved_state_invalid_time_photon_count +=1
        elif (not self.desired_state):
            # an invalid state (|early,early> or |late,late>), correctly
            #   had invalid timing
            # print(str(abs(((time - self.last_res[0]) / self.encoding["bin_separation"]) - 1.0)))
            self.invalid_state_photon_count += 1

        self.last_res = [time, detector_num]
=======
        info = {'info_type': 'BSM_res', 'res': detector_num, 'time': time, 'click_type': click_type}

        self.notify(info)
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec
