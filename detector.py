"""Models for photon detection devices.

This module models a single photon detector (SPD) for measurement of individual photons.
It also defines a QSDetector class,
which combines models of different hardware devices to measure photon states in different bases.
QSDetector is defined as an abstract template and as implementations for polarization and time bin qubits.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List
from numpy import eye, kron, exp, sqrt
from scipy.linalg import fractional_matrix_power
from math import factorial

if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline

from photon import Photon
# from sequence.beam_splitter import BeamSplitter
# from sequence.switch import Switch
# from .interferometer import Interferometer
from sequence.components.circuit import Circuit
from sequence.kernel.entity import Entity
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from encoding import time_bin, fock
from sequence.utils import log


class Detector(Entity):
    """Single photon detector device.

    This class models a single photon detector, for detecting photons.
    Can be attached to many different devices to enable different measurement options.

    Attributes:
        name (str): label for detector instance.
        timeline (Timeline): timeline for simulation.
        efficiency (float): probability to successfully measure an incoming photon.
        dark_count (float): average number of false positive detections per second.
        count_rate (float): maximum detection rate; defines detector cooldown time.
        time_resolution (int): minimum resolving power of photon arrival time (in ps).
        next_detection_count (int): ps's until detector is capable of recording
            another detection
        photon_counter (int): counts number of detection events.
        recorded_detection_count (int): counts number of detection events
            recorded (as opposed to lost due to detector efficiency)
        undetectable_photon_count (int): counts number of photons arriving
            prior to self.next_detection_time
    """

    _meas_circuit = Circuit(1)
    _meas_circuit.measure(0)

    def __init__(self, name: str, timeline: "Timeline", efficiency: float = 0.9, dark_count: float = 0, count_rate: float = 25e6, time_resolution: int = 150):
        Entity.__init__(self, name, timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = efficiency
        self.dark_count = dark_count  # measured in 1/s
        self.count_rate = count_rate  # measured in Hz
        self.time_resolution = time_resolution  # measured in ps
        self.next_detection_time = -1
        self.photon_counter = 0
        self.recorded_detection_count = 0
        self.undetectable_photon_count = 0

    def init(self):
        """Implementation of Entity interface (see base class)."""
        self.next_detection_time = -1
        self.photon_counter = 0
        if self.dark_count > 0:
            self.add_dark_count()

    def get(self, photon=None, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to detect (currently unused)

        Side Effects:
            May notify upper entities of a detection event.
        """

        self.photon_counter += 1

        # if get a photon and it has single_atom encoding, measure
        if photon and photon.encoding_type["name"] == "single_atom":
            key = photon.quantum_state
            res = self.timeline.quantum_manager.run_circuit(Detector._meas_circuit, [key], self.get_generator().random())
            # if we measure |0>, return (do not record detection)
            if not res[key]:
                return

        if self.get_generator().random() < self.efficiency:
            self.record_detection()
        else:
            log.logger.debug(f'Photon loss in detector {self.name}')

    def add_dark_count(self) -> None:
        """Method to schedule false positive detection events.

        Events are scheduled as a Poisson process.

        Side Effects:
            May schedule future `get` method calls.
            May schedule future calls to self.
        """

        assert self.dark_count > 0, "Detector().add_dark_count called with 0 dark count rate"
        time_to_next = int(self.get_generator().exponential(
                1 / self.dark_count) * 1e12)  # time to next dark count
        time = time_to_next + self.timeline.now()  # time of next dark count

        process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
        process2 = Process(self, "record_detection", [])
        event1 = Event(time, process1)
        event2 = Event(time, process2)
        self.timeline.schedule(event1)
        self.timeline.schedule(event2)

    def record_detection(self):
        """Method to record a detection event.

        Will calculate if detection succeeds (by checking if we have passed `next_detection_time`)
        and will notify observers with the detection time (rounded to the nearest multiple of detection frequency).
        """

        now = self.timeline.now()

        if now > self.next_detection_time:
            self.recorded_detection_count += 1
            time = round(now / self.time_resolution) * self.time_resolution
            self.notify({'time': time})
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps
        else:
            self.undetectable_photon_count += 1

    def notify(self, info: Dict[str, Any]):
        """Custom notify function (calls `trigger` method)."""

        for observer in self._observers:
            observer.trigger(self, info)
