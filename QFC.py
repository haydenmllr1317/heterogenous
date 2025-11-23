from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from photon import Photon
from sequence.utils import log
import numpy as np


######### TODO we want to add this QFC to the BSMNode so that it can pull from its RNG.
#########       currently, it is actually random, we want it to be pulling from the seed of BSMNode


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
        bin_separation (int): Separation time (in ps) between photon emission bins.
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

        # NOTE don't know how to handle wrong wavelength yet
        # if photon.wavelength != self.input_wvln:
        #     raise ValueError(f'{self.name} consumes wavelength of {self.input_wvln} but received photon with wavelength of {photon.wavelength}.')

        if photon.wavelength == self.input_wvln:
            # NOTE changing this, I don't think we should check is photon is lost, pump is turned on anyway
            # if self.owner.get_generator().random() >= photon.loss:
            #     photon.loss = 0 # reset loss to zero as we have already evaluated all old origins of loss
            #     photon.wavelength = self.output_wvln # actually convert the wavelength 
            #     self.send_to_receiver(photon)
            # else:
            #     log.logger.info(f'Photon lost before {self.name}.')
            self.send_to_receiver(photon)
        else:
            log.logger.warning(f'Attempted to convert {photon.wavelength}nm photon in a QFC tuned to {self.input_wvln}nm.')



    def send_to_receiver(self, photon: Photon = None):
        """
        Method to send a photon to the recieving entity.

        Args:
        photon (Photon): Input Photon object whose frequency we converted. If
                         event is a dark count, no Photon will be provided.
        """

        # noise is in range [0,1), so can just use random number generator

        photon.add_loss(1-self.efficiency) # add QFC loss

        # if self.timeline.quantum_manager.states[photon.quantum_state].state[0] != np.complex128(0.7071067811865476+0j):
        #     raise ValueError('Unprepared state is getting to QFC.')

        self.owner.conversion_counter += 1
        if self.get_generator().random() < self.noise: # noise photon added
            self.owner.qfc_noise_counter += 1
            photon.add_mode_count(1)
            self._receivers[0].get(photon)
        else: # no noise photon added
            self._receivers[0].get(photon)

