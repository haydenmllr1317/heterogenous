from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from photon import Photon
from qchannels import QuantumChannel
from custom_node import Node, BSMNode
from sequence.utils import log

class QFC(Entity):
    '''
    QFC stands for Quantum Frequency Converter. QFC is a module that is intended to convert a
    photon's wavelength from an input to an output value, as well as add in a dark count
    associated with background radiation.

    Attributes:
        name (str): Name of QFC object
        timeline (Timeline): Timeline QFC object operates on.
        input_wvln (int): Wavelength of photons QFC is meant to consume.
        output_wvln (int): Wavelength of photons QFC produces.
        efficiency (float): Number between 0 and 1 indicating probability that photon is converted properly.
        noise (float): Average number of noise photons generated per signal photon. Can assume <= 0.5.
        bin_separation (int): Separation time (in ps) between photon emission bins.
    '''
    def __init__(self, name: str, timeline: Timeline, input_wavelength = None, output_wavelength = None, efficiency = None, noise = None):
        super().__init__(name, timeline)
        self.input_wvln = input_wavelength
        self.output_wvln = output_wavelength
        self.efficiency = efficiency
        self.noise = noise
        # needed for encoding
        self.bin_separation = None

    ''' # DONT NEED ANYMORE
    def init(self) -> None:
        time_to_next = int(self.get_generator().exponential(
                1 / self.dark_count) * 1e12)  # time to first dark count
        process = Process(self, 'add_qfc_dark_count', [])
        event = Event(self.timeline.now() + time_to_next, process)
        self.timeline.schedule(event)
    '''

    def init(self) -> None:
        pass

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

        # MOVING THIS TO SEND_TO_RECEIVER
        '''
        if photon.wavelength == self.input_wvln:
            if photon.loss != 0:
                raise ValueError('Photon has unexpected nonzero loss.')
            if self.get_generator().random() <= self.efficiency:
                self.send_to_receiver(photon)
        '''

        self.send_to_receiver(photon)
        
    
    # NO LONGER DOING TIME-INDEPENDENT DARK COUNTS:
    # def add_qfc_dark_count(self) -> None:
    #     """Method to schedule false positive detection events.

    #     Events are scheduled as a Poisson process.

    #     Side Effects:
    #         May schedule future `get` method calls.
    #         May schedule future calls to self.
    #     """

    #     assert self.dark_count > 0, "Detector().add_dark_count called with 0 dark count rate"
    #     time_to_next = int(self.get_generator().exponential(
    #             1 / self.dark_count) * 1e12)  # time to next dark count
    #     time = time_to_next + self.timeline.now()  # time of next dark count
    #     self.send_to_receiver()
    #     process1 = Process(self, "add_qfc_dark_count", [])  # schedule photon detection and dark count add in future
    #     event1 = Event(time, process1)
    #     self.timeline.schedule(event1)

    def send_to_receiver(self, photon: Photon = None):
        """
        Method to send a photon to the recieving entity.

        Args:
        photon (Photon): Input Photon object whose frequency we converted. If
                         event is a dark count, no Photon will be provided.
        """

        # NO LONGER CONSIDERING DARK COUNTS
        '''
        if not photon: # if dark count, no input photon provided
            encoding = {'name': 'yb_time_bin', 'bin_separation': self.bin_separation, 'raw_fidelity': 1.0}
            photon = Photon(name='', timeline=self.timeline, wavelength=self.output_wvln, encoding_type=encoding, use_qm=False)
            photon.add_loss(float(0))
        '''

        ''' # NOT DOING THIS NOW
        dst = self.timeline.get_entity_by_name(self.receiver)

        if isinstance(dst, QuantumChannel):
            dst.transmit(photon, self)
        elif isinstance(dst, BSMNode):
            dst.receive_qubit(self.name, photon)
        else:
            raise ValueError(f'{dst.name} is an invalid destination for {self.name}.')

        '''

        # noise is in range [0,1), so can just use random number generator

        photon.add_loss(1-self.efficiency)

        if self.get_generator().random() < self.noise: # noise photon added
            photon.add_mode_count(1)
            self._receivers[0].receive_qubit(self.name, photon)
        else: # no noise photon added
            self._receivers[0].receive_qubit(self.name, photon)



        


# TODO Make QT a subclass of QFC