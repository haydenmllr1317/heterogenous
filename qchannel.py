"""Models for simulation of optical fiber channels.

This module introduces the abstract OpticalChannel class for general optical fibers.
It also defines the QuantumChannel class for transmission of qubits/photons and the ClassicalChannel class for transmission of classical control messages.
OpticalChannels must be attached to nodes on both ends.
"""

import heapq as hq
import gmpy2
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline
    from nodes import Node
    from photon import Photon

from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.utils import log
from sequence.constants import SPEED_OF_LIGHT, MICROSECOND, SECOND, EPSILON
from sequence.components.optical_channel import QuantumChannel

gmpy2.get_context().precision = 200
EPSILON_MPFR = gmpy2.mpfr(EPSILON)
PS_PER_SECOND = gmpy2.mpz(SECOND)



class HetQuantumChannel(QuantumChannel):
    """Optical channel for transmission of photons/qubits.

    Attributes:
        name (str): label for channel instance.
        timeline (Timeline): timeline for simulation.
        sender (Node): node at sending end of optical channel.
        receiver (str): name of the node at receiving end of optical channel.
        attenuation (float): attenuation of the fiber (in dB/m).
        distance (float): length of the fiber (in m).
        polarization_fidelity (float): probability of no polarization error for a transmitted qubit.
        light_speed (float): speed of light within the fiber (in m/ps).
        loss (float): loss rate for transmitted photons (determined by attenuation).
        delay (int): delay (in ps) of photon transmission (determined by light speed, distance).
        frequency (float): maximum frequency of qubit transmission (in Hz).
    """

    def __init__(self, name: str, timeline: "Timeline", attenuation: float, distance: float,
                 polarization_fidelity: float = 1.0, light_speed: float = SPEED_OF_LIGHT, frequency: float = 8e7, qfc: str = None):
        """Constructor for Quantum Channel class.

        Args:
            name (str): name of the quantum channel instance.
            timeline (Timeline): simulation timeline.
            attenuation (float): loss rate of optical fiber (in dB/m).
            distance (float): length of fiber (in m).
            polarization_fidelity (float): probability of no polarization error for a transmitted qubit (default 1).
            light_speed (float): speed of light within the fiber (in m/ps).
            delay (int): delay (in ps) of photon transmission (determined by light speed, distance).
            loss (float): loss rate for transmitted photons (determined by attenuation).
            frequency (float): maximum frequency of qubit transmission (in Hz) (default 8e7).
        """

        super().__init__(name, timeline, attenuation, distance, polarization_fidelity, light_speed, frequency)
        self.qfc = qfc # NOTE NEW

    # NOTE overwrote to ensure photon goes to QFC before node
    def transmit(self, qubit: "Photon", source: "Node") -> None:
        """Method to transmit photon-encoded qubits.

        Args:
            qubit (Photon): photon to be transmitted.
            source (Node): source node sending the qubit.

        Side Effects:
            Receiver node may receive the qubit (via the `receive_qubit` method).
        """

        log.logger.info("{} send qubit with state {} to {} by Channel {}".format(
                        self.sender.name, qubit.quantum_state, self.receiver, self.name))

        assert self.delay >= 0 and self.loss < 1, f"QuantumChannel init() function has not been run for {self.name}"
        assert source == self.sender

        # remove lowest time bin
        if len(self.send_bins) > 0:
            time = -1
            while time < self.timeline.now():
                time_bin = hq.heappop(self.send_bins)
                time = self.timebin_to_time(time_bin, self.frequency)
            assert time == self.timeline.now(), f"qc {self.name} transmit method called at invalid time"

        # check if photon state using Fock representation
        if qubit.encoding_type["name"] == "fock":
            key = qubit.quantum_state  # if using Fock representation, the `quantum_state` field is the state key.
            # apply loss channel on photonic statex
            self.timeline.quantum_manager.add_loss(key, self.loss)

            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + self.delay
            process = Process(self.receiver, "receive_qubit", [source.name, qubit])
            event = Event(future_time, process)
            self.timeline.schedule(event)

        # if not using Fock representation, check if photon kept
        elif (self.sender.get_generator().random() > self.loss) or qubit.is_null:
            if self._receiver_on_other_tl():
                self.timeline.quantum_manager.move_manage_to_server(qubit.quantum_state)

            if qubit.is_null:
                qubit.add_loss(self.loss)

            # check if polarization encoding and apply necessary noise
            if qubit.encoding_type["name"] == "polarization" and self.sender.get_generator().random() > self.polarization_fidelity:
                qubit.random_noise(self.get_generator())

            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + self.delay
            if self.qfc:
                process = Process(self.qfc, "receive_qubit", [source.name, qubit])
            else:
                process = Process(self.receiver, "receive_qubit", [source.name, qubit])
            event = Event(future_time, process)
            self.timeline.schedule(event)

        # if not using Fock representation, if photon lost, exit
        else:
            pass