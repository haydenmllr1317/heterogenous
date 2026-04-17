"""Model for single photon in heterogenous network simulation. # NOTE HM DONE whole file

This module defines the HetPhoton class for tracking individual photons.
HetPhoton class inherits directly from Photon class, and simply adds a few attribute.
Photons may be encoded directly with polarization or time bin schemes, or may herald the encoded state of single atom memories.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline

from encoding import polarization
from sequence.components.photon import Photon


class HetPhoton(Photon):
    """Class for a single photon, modified for heterogenous network simulation.

    Attributes:
        name (str): label for photon instance.
        wavelength (float): wavelength of photon (in nm).
        location (Entity): current location of photon.
        encoding_type (Dict[str, Any]): encoding type of photon (as defined in encoding module).
        quantum_state (Union[int, Tuple[complex]]): quantum state of photon.
            If `use_qm` is false, this will be a QuantumState object.
            Otherwise, it will be an integer key for the quantum manager.
        is_null (bool): defines whether photon is real or a "ghost" photon (not detectable but used in memory encoding).
                        if True, then it is a "ghost" photon
        loss (float): similarly defined for memory encoding, used to track loss and improve performance.
            Does not need to be utilized for all encoding schemes.
        use_qm (bool): determines if photon stores state locally (False) or uses timeline quantum manager (True).
        qfc_noise_count (int): number of noise photons from a QFC encapsulated in this object (in the same mode).
        qfc_transducer_count (int): number of noise photons from a transducer encapsulated in this object (in the same mode).
        contains_signal (bool): whether this photon object contains a signal photon or not.
        only_early (bool): whether this photon only has the early bin of a time bin encoding, due to decoherence during generation.
    """

    def __init__(self, name: str, timeline: "Timeline", wavelength=0, location=None, encoding_type=polarization, quantum_state=None, use_qm=False):
        """Constructor for the photon class.

        Args:
            name (str): name of the photon instance.
            timeline (Timeline): simulation timeline reference
            wavelength (int): wavelength of photon (in nm) (default 0).
            location (Entity): location of the photon (default None).
            encoding_type (Dict[str, Any]): encoding type of photon (from encoding module) (default polarization).
            quantum_state (Union[int, Tuple[complex]]):
                reference key for quantum manager, or complex coefficients for photon's quantum state.
                Default state is (1, 0).
                If left blank and `use_qm` is true, will create new key from timeline quantum manager.
            use_qm (bool): determines if the quantum state is obtained from the quantum manager or stored locally.
        """

        super().__init__(name, timeline, wavelength, location, encoding_type, quantum_state, use_qm)

        self.qfc_noise_count = 0                            # number of QFC noise photons in this mode
        self.transducer_noise_count = 0                     # number of transducer noise photons in this mode
        self.contains_signal: bool = True                   # if contains signal photon or not
        self.only_early = False                             # true if decoheres during generation (in bin separation time)