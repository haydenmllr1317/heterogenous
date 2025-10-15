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
        
        self.encoding = photon.encoding_type

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
        self.early_early = 0 # currently not using
        self.early_late = 0 # currently not using
        self.late_early = 0 # currently not using
        self.late_late = 0 # currently not using
        self.desired_state = None # currently not using
        self.trigger_count = 0
        self.appropriate_time_photon_count = 0
        self.approved_state_invalid_time_photon_count = 0
        self.invalid_state_photon_count = 0

        self.time_bin_separation = None
        self.average_bin_size = None # size of our time bins
        
        self.trigger_times = [] # list of when recent photons arrived at BSM
        self.signal_values = [] # list of booleans determining whether recent photons were signals or not
        self.detector_hits = [] # list of recent detectors clicked
        
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

        # UNCLEAR WHAT THIS IS FROM/FOR
        # while len(self.photons) > 1:
        #     self.photons = self.photons[1:]

        # if round((self.timeline.now() - self.photon_arrival_time)/self.encoding["bin_separation"]) == 1:
        #     self.photons.append(photon)
        # else:
        #     self.photons = [photon]
        
        # self.photon_arrival_time = self.timeline.now()

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

            late_time = self.timeline.now() + self.time_bin_separation

            p0_odds = self.get_generator().random()
            p1_odds = self.get_generator().random()

            if (not meas0) and (not meas1): # early and early
                self.early_early += 1
                self.desired_state = False # photons are not early/late or late/early
                # HOM interference gives same detector
                detector_num_signal = self.get_generator().choice([0,1])
                if p0_odds > p0.loss: # first early photon surives
                    self.detectors[detector_num_signal].get()
                else:                 # first early photon is lost
                    log.logger.info(f'{self.name} lost photon p0 signal')

                if p1_odds > p1.loss: # second early photon surives
                    self.detectors[detector_num_signal].get()
                else:                 # second early photon is lost
                    log.logger.info(f'{self.name} lost photon p1')

                if p0.mode_count > 1: # photon 0 has noise
                    detector_num0_noise = self.get_generator().choice([0,1])
                    self.detectors[detector_num0_noise].get()
                    log.logger.info(f'{self.name} sent p0 noise photon to detector {detector_num0_noise} at early time bin.')
                if p1.mode_count > 1: # photon 1 has noise
                    detector_num1_noise = self.get_generator().choice([0,1])
                    self.detectors[detector_num1_noise].get()
                    log.logger.info(f'{self.name} sent p1 noise photon to detector {detector_num1_noise} at early time bin.')
            
            elif (not meas0) and meas1: # early and late
                self.early_late += 1
                detector_num0 = self.get_generator().choice([0,1])       # detector for photon p0
                detector_num1 = self.get_generator().choice([0,1])       # detector for photon p1
                detector_num0_noise = self.get_generator().choice([0,1]) # detector for photon p0 noise
                detector_num1_noise = self.get_generator().choice([0,1]) # detector for photon p1 noise
                get_args = {} # has 'signal': True  if early/late photons both are lossless and noiseless

                if p0_odds > p0.loss and p1_odds > p1.loss:
                    self.desired_state = True # photons are early/late or late/early
                    if p0.mode_count == 1 and p1.mode_count == 1: # only signal photons in the mode
                        get_args = {'signal': True}
                        if detector_num0 == detector_num1: # set to psi_plus state
                            _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"], self.get_generator(), qm) # implicitly assuming the two photons have the same fidelity (which is 1 in this case)
                        else:                              # set to psi_minus states
                            _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"], self.get_generator(), qm) # implicitly assuming the two photons have the same fidelity (which is 1 in this case)
                else:
                    self.desired_state = False

                if p0_odds > p0.loss: # early photon survives
                    self.detectors[detector_num0].get(**get_args)
                else:                 # early photon lost
                    log.logger.info(f'{self.name} lost photon p0')

                if p1_odds > p1.loss: # late photon survives
                    process = Process(self.detectors[detector_num1], "get", [], get_args)
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:                 # late photon lost
                    log.logger.info(f'{self.name} lost photon p1')

                if p0.mode_count > 1: # early photon noise
                    self.detectors[detector_num0_noise].get()
                    log.logger.info(f'{self.name} sent p0 noise photon to detector {detector_num0_noise} at early time bin.')
                if p1.mode_count > 1: # late photon noise
                    process = Process(self.detectors[detector_num1_noise], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                    log.logger.info(f'{self.name} sent p1 noise photon to detector {detector_num1_noise} at late time bin.')

            elif meas0 and (not meas1): # late and early
                self.late_early += 1
                detector_num0 = self.get_generator().choice([0,1])       # detector for photon p0
                detector_num1 = self.get_generator().choice([0,1])       # detector for photon p1
                detector_num0_noise = self.get_generator().choice([0,1]) # detector for photon p0 noise
                detector_num1_noise = self.get_generator().choice([0,1]) # detector for photon p1 noise
                get_args = {} # has 'signal': True  if late/early photons both are lossless and noiseless

                if p0_odds > p0.loss and p1_odds > p1.loss:
                    self.desired_state = True # photons are early/late or late/early
                    if p0.mode_count == 1 and p1.mode_count == 1: # only signal photons in the mode
                        get_args = {'signal': True}
                        if detector_num0 == detector_num1: # set to psi_plus state
                            _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"], self.get_generator(), qm)
                        else:                              # set to psi_minus states
                            _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"], self.get_generator(), qm)
                else:
                    self.desired_state = False

                if p0_odds > p0.loss: # late photon survives
                    process = Process(self.detectors[detector_num0], "get", [], get_args)
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:                 # late photon lost
                    log.logger.info(f'{self.name} lost photon p0')

                if p1_odds > p1.loss: # early photon survives
                    self.detectors[detector_num1].get(**get_args)
                else:                 # early photon lost
                    log.logger.info(f'{self.name} lost photon p0')

                if p0.mode_count > 1: # late photon noise
                    process = Process(self.detectors[detector_num0_noise], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                    log.logger.info(f'{self.name} sent p0 noise photon to detector {detector_num0_noise} at late time bin.')
                if p1.mode_count > 1: # early photon noise
                    self.detectors[detector_num1_noise].get()
                    log.logger.info(f'{self.name} sent p1 noise photon to detector {detector_num1_noise} at early time bin.')


            elif meas0 and meas1: # late and late
                self.late_late += 1
                self.desired_state = False
                # HOM interference gives same detector
                detector_num_signal = self.get_generator().choice([0,1])
                if p0_odds > p0.loss: # first late photon surives
                    process = Process(self.detectors[detector_num_signal], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:                 # first late photon is lost
                    log.logger.info(f'{self.name} lost photon p0 signal')

                if p1_odds > p1.loss: # second late photon surives
                    process = Process(self.detectors[detector_num_signal], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                else:                 # second late photon is lost
                    log.logger.info(f'{self.name} lost photon p1 signal')

                if p0.mode_count > 1: # photon 0 has noise
                    detector_num0_noise = self.get_generator().choice([0,1])
                    process = Process(self.detectors[detector_num0_noise], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                    log.logger.info(f'{self.name} sent p0 noise photon to detector {detector_num0_noise} at late time bin.')
                if p1.mode_count > 1: # photon 1 has noise
                    detector_num1_noise = self.get_generator().choice([0,1])
                    process = Process(self.detectors[detector_num1_noise], "get", [])
                    event = Event(late_time, process)
                    self.timeline.schedule(event)
                    log.logger.info(f'{self.name} sent p1 noise photon to detector {detector_num1_noise} at late time bin.')
    

    #### NO LONGER USING
    # def get(self, photon, **kwargs):
    #     """
    #     This method simply triggers a random detector due to its input photon and passes on the
    #     quantum_state key of the photon if the photon has a quantum manager. Only input photons
    #     eminating from our nodes have quantum managers, QFC noise photons don't.
    #     """
    #     detector_num = self.get_generator().choice([0,1]) # which detector photon goes to
    #     if photon.use_qm: # tells us is a photon from our nodes
    #         self.detectors[detector_num].get(photon=None, qstate_key=photon.quantum_state)
    #     else: # tells us is a 'fake' photon from QFC noise
    #         self.detectors[detector_num].get(photon=None)

    #     # we could add HOM interference, but it doesn't really impact anything so idk if we care

    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """

        This class is called in the Detector modules to indicate a detector
        was clicked. It consumes:

        detector(Detector) - what detector click comes from
        info (Dict[str, Any]) - contains time of click and possibly the quantum_state key
            of the "real" (not noise) photon that triggered the detector.

        """

        self.trigger_count += 1
        time = info["time"] # time detector was triggered
        try:
            signal = info["signal"] # if real photon caused trigger (as opposed to dc), we should have a key
        except Exception:
            signal = False

        detector_num = self.detectors.index(detector)

        while self.trigger_times: # list of recent detector trigger times
            dt = time - self.trigger_times[0] # time distance between current and oldest click
            detector_resolution = self.detectors[self.detector_hits[0]].time_resolution
            
            error_bar = detector_resolution + self.average_bin_size # uncertainty about allowed detector click time distance

            if (dt-error_bar) >= self.time_bin_separation: # oldest and current clicks are too distant
                # Too old → discard
                self.trigger_times.pop(0)
                self.signal_values.pop(0)
                self.detector_hits.pop(0)
            
            elif (dt+error_bar) <= self.time_bin_separation: # oldest and current clicks are too close
                # do nothing, wait for future clicks
                break # was pass and switched it 

            else: # oldest click and current click are bin_seperation apart
                # Matching interval → possible BSM event
                old_signal = self.signal_values[0]
                old_detector = self.detector_hits[0]

                if detector_num == old_detector:
                    info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 0, 'time': time}
                else:
                    info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 1, 'time': time}
                if not (old_signal and signal):
                    log.logger.warning('Potential dark count state (correct timing interval).')
                self.notify(info)
                break  # stop as we found our appropriately separated clicks

        self.trigger_times.append(time)
        self.signal_values.append(signal)
        self.detector_hits.append(detector_num)

        


        ### OLD TRIGGER CODE

        # self.trigger_count += 1
        
        # time = info["time"]

        # log.logger.info(self.name + ' was triggered by ' + detector.name)

        # # check if valid time
        # if round((time - self.last_res[0]) / self.encoding["bin_separation"]) == 1: # two most recent detector clicks have time bin seperation
        #     if (not self.desired_state): # most recent measured photons were early/early or late/late 
        #         # an 'undesired state' is one that is either |early,early>
        #         #   or |late,late>. thus the photons' timing should be
        #         #   negligible compared to the bin_separation
        #         log.logger.error('An undesired state had correct timing due to detector dark count.')

        #     self.appropriate_time_photon_count += 1
        #     # Psi+
        #     if detector_num == self.last_res[1]:
        #         info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 0, 'time': time}
        #         self.notify(info)
        #     # Psi-
        #     else:
        #         info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 1, 'time': time}
        #         self.notify(info)
        # else: # no detector click occured time-bin separation prior to this one
        #     if self.desired_state: # most recent measured photons were early/late or late/early, but some photon was lost or had noise
        #         self.approved_state_invalid_time_photon_count +=1
        #     else: # most recent photons were measured as early/early or late/late
        #         self.invalid_state_photon_count += 1
        # self.last_res = [time, detector_num]


