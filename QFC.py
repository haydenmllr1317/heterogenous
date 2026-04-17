from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from photon import Photon
from sequence.utils import log
import numpy as np


class QFC(Entity):
    '''
    QFC stands for Quantum Frequency Converter. QFC is a module that is intended to convert a
    photon's wavelength from an input to an output value, as well as add in conversion noise.

    Attributes:
        name (str): Name of QFC object
        timeline (Timeline): Timeline QFC object operates on.
        input_wvln (int): Wavelength of photons QFC is meant to consume.
        output_wvln (int): Wavelength of photons QFC produces.
        efficiency (float): Number between 0 and 1 indicating probability that photon is converted properly.
        noise (float): Average number of noise photons generated per signal photon. Can assume <= 0.5.
    '''
    def __init__(self, name: str, timeline: Timeline, input_wavelength = None, output_wavelength = None, efficiency = None, noise = None):
        super().__init__(name, timeline)
        self.input_wvln = input_wavelength
        self.output_wvln = output_wavelength
        self.efficiency = efficiency
        self.noise = noise

    def init(self) -> None:
        pass

    def get(self, photon: Photon): 
        '''
        Method to receive photon and take further action.
        If the photon has the correct wavelength and isn't too lossy, we 
        send the photon onto this QFC's receiver. Otherwise, we do nothing.

        Args:
        photon (Photon): Photon objected being converted.
        '''
        # log.logger.info(f'{self.name} received a photon')

        # okay let's do a scenario tree
        # Yb-Yb link:
        #    - there is no noise
        #    - we just want to make sure if it's the wrong wavelength it doens't get to detector
        # Yb-uW link:
        #    - there is QFC noise we add here, so we want a photon to go through (if only just noise)
        #    - I could just have a signal bool and a noise count

        # NOTE don't know how to handle wrong wavelength yet
        # if photon.wavelength != self.input_wvln:
        #     raise ValueError(f'{self.name} consumes wavelength of {self.input_wvln} but received photon with wavelength of {photon.wavelength}.')

        # Yb atom decayed incorrectly
        if photon.wavelength != self.input_wvln:
            photon.contains_signal = False
        
        photon.wavelength = self.output_wvln # set photon wavelength

        photon.add_loss(1-self.efficiency) # e
        self.send_to_receiver(photon)



    def send_to_receiver(self, photon: Photon = None):
        """
        Method to send a photon to the recieving entity.

        Args:
        photon (Photon): Input Photon object whose frequency we converted. If
                         event is a dark count, no Photon will be provided.
        """

        # noise is in range [0,1), so can just use random number generator
        # if self.timeline.quantum_manager.states[photon.quantum_state].state[0] != np.complex128(0.7071067811865476+0j):
        #     raise ValueError('Unprepared state is getting to QFC.')

        self.owner.conversion_counter += 1
        if self.get_generator().random() < self.noise: # noise photon added
            photon.qfc_noise_count = 1
            self._receivers[0].get(photon)
        else: # no noise photon added
            self._receivers[0].get(photon)

