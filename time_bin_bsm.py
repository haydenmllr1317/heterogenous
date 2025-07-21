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


class BSM(Entity):
    """Parent class for bell state measurement devices.

    Attributes:
        name (str): label for BSM instance.
        timeline (Timeline): timeline for simulation.
        phase_error (float): phase error applied to measurement.
        detectors (List[Detector]): list of attached photon detection devices.
        resolution (int): maximum time resolution achievable with attached detectors.
    """

    _phi_plus = [complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))]
    _phi_minus = [complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))]
    _psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]
    _psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]

    def __init__(self, name: str, timeline: "Timeline", phase_error: float = 0, detectors=None):
        """Constructor for base BSM object.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): Phase error applied to polarization photons (default 0).
            detectors (List[Dict[str, Any]]): List of parameters for attached detectors,
                in dictionary format (default None).
        """

        super().__init__(name, timeline)
        self.encoding = "None"
        self.phase_error = phase_error
        self.photons = []
        self.photon_arrival_time = -1
        self.resolution = None

        self.detectors = []
        if detectors is not None:
            for i, d in enumerate(detectors):
                if d is not None:
                    detector = Detector("{}_{}".format(self.name, i), timeline, **d)
                    detector.attach(self)
                    detector.owner = self
                else:
                    detector = None
                self.detectors.append(detector)

        # define bell basis vectors
        self.bell_basis = ((complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))),
                           (complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))),
                           (complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)),
                           (complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)))

    def init(self):
        """Implementation of Entity interface (see base class)."""

        # get resolution
        self.resolution = max(d.time_resolution for d in self.detectors)

        self.photons = []
        self.photon_arrival_time = -1

    @abstractmethod
    def get(self, photon, **kwargs):
        """Method to receive a photon for measurement (abstract).

        Arguments:
            photon (Photon): photon to measure.
        """
        # NOTE: CHANGED THIS TO REFLECT ENCODING IS NOW A DICT
        assert photon.encoding_type["name"] == self.encoding["name"], \
            "BSM expecting photon with encoding '{}' received photon with encoding '{}'".format(
                self.encoding, photon.encoding_type["name"])

        # check if photon arrived later than current photon
        if self.photon_arrival_time < self.timeline.now():
            # clear photons
            self.photons = [photon]
            # set arrival time
            self.photon_arrival_time = self.timeline.now()

        # check if we have a photon from a new location
        if not any([reference.location == photon.location for reference in self.photons]):
            self.photons.append(photon)

    @abstractmethod
    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """Method to receive photon detection events from attached detectors (abstract).

        Arguments:
            detector (Detector): the source of the detection message.
            info (Dict[str, Any]): the message from the source detector.
        """

        pass

    def notify(self, info: Dict[str, Any]):
        for observer in self._observers:
            observer.bsm_update(self, info)

    def update_detectors_params(self, arg_name: str, value: Any) -> None:
        """Updates parameters of attached detectors."""
        for detector in self.detectors:
            detector.__setattr__(arg_name, value)

class TimeBinBSM(BSM):
    """Class modeling a time bin BSM device.

    Measures incoming photons according to time bins and manages entanglement.

    Attributes:
        name (str): label for BSM instance
        timeline (Timeline): timeline for simulation
        detectors (List[Detector]): list of attached photon detection devices
        phase_error (float): phase error applied to polarization qubits (unused)
        encoding(float): 'time_bin', used in 'BSM' class to ensure recieved
            photon is of the same encoding type
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

    def __init__(self, name, timeline, encoding, phase_error=0, detectors=None):
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

        self.encoding = encoding
        self.last_res = [-1, -1]
        self.early_early = 0
        self.early_late = 0
        self.late_early = 0
        self.late_late = 0
        self.desired_state = None
        self.trigger_count = 0
        self.appropriate_time_photon_count = 0
        self.approved_state_invalid_time_photon_count = 0
        self.invalid_state_photon_count = 0
        
        # for our BSM setup...
        assert len(self.detectors) == 2

    def get(self, photon, **kwargs):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        super().get(photon)
        log.logger.debug(self.name + " recieved 'photon' quantum information")
        
        if len(self.photons) == 2:
            qm = self.timeline.quantum_manager
            p0, p1 = self.photons
            key0, key1 = p0.quantum_state, p1.quantum_state
            keys = [key0, key1]
            # measurement results here are considered in the {early,late} basis
            meas0, meas1 = [qm.run_circuit(self._meas_circuit, [key], self.get_generator().random())[key]
                            for key in keys]
            
            log.logger.debug(self.name + " measured photons as {}, {}".format(meas0,meas1))

            late_time = self.timeline.now() + self.encoding["bin_separation"]

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


    # this class should call self.notify(info) only if the photon
    #   that caused the trigger event was the second photon in a 
    #   pair that was in one of the approved |early,late> or |late,early> states
    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May send a further message to any attached entities.
        """

        self.trigger_count += 1
        detector_num = self.detectors.index(detector)
        time = info["time"]

        log.logger.info(self.name + ' was triggered by ' + detector.name)

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