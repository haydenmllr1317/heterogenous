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
from sequence.components.bsm import BSM, _set_state_with_fidelity



# BSM class is same as in SeQUeNCE, just have it here as it helps to bug check
# via logging and print statement etc
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

        assert photon.encoding_type["name"] == self.encoding, \
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

# altered from SeQUeNCE version, changes have 'NOTE' by them
class TimeBinBSM(BSM):
    """Class modeling a time bin BSM device.

    Measures incoming photons according to time bins and manages entanglement.

    Attributes:
        name (str): label for BSM instance
        timeline (Timeline): timeline for simulation
        detectors (List[Detector]): list of attached photon detection devices
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

        # NOTE: create a empty list of dictionaries for compatability with
        #       with BSM class
        if detectors is None:
            detectors = [{}, {}]
        # NOTE: END OF CHANGES

        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = "time_bin"
        self.encoding_type = time_bin
        self.last_res = [-1, -1]

        # NOTE: al stupid bug checking constants
        self.ee = 0
        self.el = 0
        self.le = 0
        self.ll = 0
        self.current = -1
        self.wrongs = 0
        self.throw_aways = 0
        self.triggered = 0
        self.got_right_away = 0
        self.got_later = 0
        self.nada = -1
        self.good_ones = 0
        
        # NOTE: added just to make sure
        assert len(self.detectors) == 2

    # NOTE: this is just entirely different, modeled more off of SingleAtomBSM
    #       class
    def get(self, photon, **kwargs):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        super().get(photon)
        log.logger.debug(self.name + " recieved photon")
        
        if len(self.photons) == 2:
            qm = self.timeline.quantum_manager
            p0, p1 = self.photons
            key0, key1 = p0.quantum_state, p1.quantum_state
            keys = [key0, key1]
            state0, state1 = qm.get(key0), qm.get(key1)
            meas0, meas1 = [qm.run_circuit(self._meas_circuit, [key], self.get_generator().random())[key]
                            for key in keys]
            # NOTE: results of meas0,meas1 are thought of as in the E,L basis
            
            log.logger.debug(self.name + " measured photons as {}, {}".format(meas0,meas1))

            late_time = self.timeline.now() + self.encoding_type["bin_separation"]

            if (not meas0) and (not meas1):
                self.ee += 1
                self.current = 0
                self.nada = 1
                # HOM interference gives same detector
                detector_num = self.get_generator().choice([0,1])
                if self.get_generator().random() > p0.loss:
                    self.got_right_away +=1
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p0')

                if self.get_generator().random() > p1.loss:
                    self.got_right_away +=1
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p1')
            
            elif (not meas0) and meas1:
                self.el += 1
                self.current = 1
                self.nada = 0
                detector_num1 = self.get_generator().choice([0,1])
                detector_num2 = self.get_generator().choice([0,1])
                if detector_num1 == detector_num2:
                    _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"],
                    self.get_generator(), qm)
                else:
                    _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"],
                    self.get_generator(), qm)
                if self.get_generator().random() > p0.loss:
                    self.got_right_away +=1
                    self.detectors[detector_num1].get()
                else:
                    log.logger.info(f'{self.name} lost photon p0')
                if self.get_generator().random() > p1.loss:
                    self.got_later +=1
                    process = Process(self.detectors[detector_num2], "get", [])
                    event = Event(int(round(late_time)), process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p1')

            elif meas0 and (not meas1):
                self.le += 1
                self.nada = 0
                self.current = 1
                detector_num1 = self.get_generator().choice([0,1])
                detector_num2 = self.get_generator().choice([0,1])
                if detector_num1 == detector_num2:
                    _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"],
                    self.get_generator(), qm)
                else:
                    _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"],
                    self.get_generator(), qm)
                if self.get_generator().random() > p0.loss:
                    self.got_later +=1
                    process = Process(self.detectors[detector_num1], "get", [])
                    event = Event(int(round(late_time)), process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p0')
                if self.get_generator().random() > p1.loss:
                    self.got_right_away +=1
                    self.detectors[detector_num2].get()
                else:
                    log.logger.info(f'{self.name} lost photon p1')

            elif meas0 and meas1:
                self.ll +=1
                self.current = 0
                self.nada = 0
                # HOM interference gives same detector
                detector_num = self.get_generator().choice([0,1])
                if self.get_generator().random() > p0.loss:
                    self.got_later +=1
                    process = Process(self.detectors[detector_num], "get", [])
                    event = Event(int(round(late_time)), process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p0')
                if self.get_generator().random() > p1.loss:
                    self.got_later +=1
                    process = Process(self.detectors[detector_num], "get", [])
                    event = Event(int(round(late_time)), process)
                    self.timeline.schedule(event)
                else:
                    log.logger.info(f'{self.name} lost photon p1')


    # this class should call self.notify(info) only if the photon
    #   that caused the trigger event was the second photon in a 
    #   pair that was in one of the approved |EL> or |LE> states
    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May send a further message to any attached entities.
        """

        self.triggered += 1

        detector_num = self.detectors.index(detector)
        time = info["time"]

        # check if valid time
        if round((time - self.last_res[0]) / self.encoding_type["bin_separation"]) == 1:
            if (not self.current): raise ValueError('ee or ll slipt through')

            # Psi+
            self.good_ones += 1
            if detector_num == self.last_res[1]:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 0, 'time': time}
                self.notify(info)
            # Psi-
            else:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 1, 'time': time}
                self.notify(info)
        elif self.current:
            self.wrongs += 1
        elif (not self.current):
            self.throw_aways += 1

        self.last_res = [time, detector_num]