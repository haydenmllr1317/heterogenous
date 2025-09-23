from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from photon import Photon
from qchannels import QuantumChannel
from custom_node import Node, BSMNode
from sequence.utils import log

class QFC(Entity):
    def __init__(self, name: str, timeline: Timeline, receiver: Entity, input_wavelength = None, output_wavelength = None, efficiency = None, dark_count = None):
        super().__init__(name, timeline)
        self.receiver = receiver
        self.input_wvln = input_wavelength
        self.output_wvln = output_wavelength
        self.efficiency = efficiency
        self.dark_count = dark_count
        # needed for encoding
        self.bin_separation = None

    def init(self) -> None:
        self.add_qfc_dark_count()

    def receive_qubit(self, source_name: str, photon: Photon):
        log.logger.info(f'{self.name} received a photon from {source_name}')
        # NOTE don't know how to handle wrong wavelength yet
        # if photon.wavelength != self.input_wvln:
        #     raise ValueError(f'{self.name} consumes wavelength of {self.input_wvln} but received photon with wavelength of {photon.wavelength}.')
        # NOTE might want to add this type of efficiency
        # try:
        #     efficiency = self.efficiency[self.input_wvln][self.output_wvln]
        # except Exception as e:
        #     raise ValueError(f"{self.name} isn't equipped to transform between {self.input_wvln} and {self.output_wvln}.")
        if photon.wavelength == self.input_wvln:
            efficiency = self.efficiency
            photon.add_loss(1-efficiency)
            self.send_to_receiver(photon)
    
    def add_qfc_dark_count(self) -> None:
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
        process1 = Process(self, "add_qfc_dark_count", [])  # schedule photon detection and dark count add in future
        process2 = Process(self, "send_to_receiver", [])
        event1 = Event(time, process1)
        event2 = Event(time, process2)
        self.timeline.schedule(event1)
        self.timeline.schedule(event2)

    def send_to_receiver(self, photon: Photon = None):
        if not photon:
            encoding = {'name': 'yb_time_bin', 'bin_separation': self.bin_separation, 'raw_fidelity': 1.0}
            photon = Photon(name='', timeline=self.timeline, wavelength=self.output_wvln, encoding_type=encoding, use_qm=True)
            photon.add_loss(float(0))

        dst = self.timeline.get_entity_by_name(self.receiver)

        if isinstance(dst, QuantumChannel):
            dst.transmit(photon, self)
        elif isinstance(dst, BSMNode):
            dst.receive_qubit(self.name, photon)
        else:
            raise ValueError(f'{dst.name} is an invalid destination for {self.name}.')
        
