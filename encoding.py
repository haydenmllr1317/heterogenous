'''

Encoding is same as SeQUeNCe's except the time_bin bin_separation is 50,000.

'''


"""Definitions of encoding schemes.

Encoding schemes are applied to photons and memories to track how quantum information is stored.
This includes the name of the encoding scheme, bases available, and any other necessary parameters.

Attributes:
    polarization (Dict[str, any]): defines the polarization encoding scheme, including the Z- and X-basis.
    time_bin (Dict[str, any]): defines the time bin encoding scheme, including the Z- and X-basis. Also defines the bin separation time.
    single_atom (Dict[str, any]): defines the emissive memory scheme, including the Z-basis.
    absorptive (Dict[str, any]): defines the absorptive memory scheme, including the Z-basis.
"""

from math import sqrt


polarization =\
    {"name": "polarization",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))),
               ((complex(sqrt(1 / 2)), complex(sqrt(1 / 2))), (complex(-sqrt(1 / 2)), complex(sqrt(1 / 2))))]
     }

time_bin = \
    {"name": "time_bin",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))),
               ((complex(sqrt(1 / 2)), complex(sqrt(1 / 2))), (complex(sqrt(1 / 2)), complex(-sqrt(1 / 2))))],
     "raw_fidelity": 1,
     "bin_separation": 50000 # 1400  # measured in ps
     }

# single_atom must be copied by a memory object so the fidelity field can be overwritten
single_atom = \
    {"name": "single_atom",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))), None],
     "raw_fidelity": 1,
     "keep_photon": True
     }

absorptive = \
    {"name": "absorptive",
     "bases": [((complex(1), complex(0)), (complex(0), complex(1))), None]
     }

fock = \
    {"name": "fock",
     "bases": None
     }

single_heralded = \
    {"name": "single_heralded",
     "bases": None,
     "keep_photon": True
     }
