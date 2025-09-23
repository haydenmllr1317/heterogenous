'''
This file is to try and do realistic simulation of entanglement generation
between two single-atom yb nodes. We will be using what we believe are realistic
parameters and mapping average time and attempts required to get entanglement.

NOTE: ADD MORE INFO HERE

'''


from sequence.kernel.timeline import Timeline
from custom_node import Node, BSMNode
from memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from qchannels import QuantumChannel
from generation import EntanglementGenerationTimeBinYb
from sequence.message import Message
from sequence.utils import log
import plotly.graph_objects as go
from encoding import yb_time_bin
from copy import copy
from yb_router_net_topo import RouterNetTopo
from request_app import RequestApp
from math import inf
import argparse
import time
from memory import MemoryArray



ent = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-pce', '--photoncollectionefficiency', type=float, default=0.253, help='efficiency of photon collection into fiber')
    parser.add_argument('-wavelength', '--photonwavelength', type=int, default=1389, help='wavelength of emmitted photons')
    parser.add_argument('-t_retrap', '--time_to_retrap', type=int, default=40, help="Time atom has been in trap at which we want to retrap (in seconds).")
    parser.add_argument('-n', '--numtrials', type=int, default=200, help="number of entangled pairs we generated")
    parser.add_argument('-dtctor_dc', '--detectordarkcount', type=float, default=11.0, help="Dark count rate, in Hz, for the detector in the BSM.")
    parser.add_argument('-bsm_wvln', '--bsm_operating_wavelength', type=int, default=746, help="Photon wavelength BSM ideally operates at.")
    parser.add_argument('-qfc_eff', '--qfc_efficiency', type=float, default=0.9, help="Efficiency of our quantum frequency converters.")
    parser.add_argument('-qfc_dc', '--qfc_dark_count_rate', type=float, default=10.0, help="Dark count rates (Hz) in our quantum frequency converters.")


    args = parser.parse_args()
    photon_collection_efficiency = args.photoncollectionefficiency
    wavelength = args.photonwavelength
    retrap_time = args.time_to_retrap * 1e12
    n = args.numtrials
    detector_dark_count = args.detectordarkcount
    bsm_operating_wavelength = args.bsm_operating_wavelength
    qfc_eff = args.qfc_efficiency
    qfc_dc = args.qfc_dark_count_rate


    # NOTE: I don't think I need encodings anymore?
    # yb_enc = copy(yb_time_bin)

    network_config = 'linear.json'
    network_topo = RouterNetTopo(network_config)

    tl = network_topo.get_timeline()
    encoding_name = 'TimeBinBSM'

    # use encoding_name to grab encoding-appropriate BSM object
    bsm = network_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)[0].get_components_by_type(encoding_name)[0]
    bsm.update_detectors_params('efficiency', 0.85) # according to Joaquin should be .85
    bsm.update_detectors_params('dark_count', detector_dark_count)


    # logging added here
    # log_filename = f'pce={photon_collection_efficiency},lambda={wavelength},num_trials={n}.log'
    log_filename = f'data/fid(qfc_dc)/qfc_dc={qfc_dc}.log'
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('WARNING')
    log.track_module('generation')
    log.track_module('bsm')
    log.track_module('detector')
    log.track_module('memory')
    log.track_module('photon')
    log.track_module('custom_node')
    log.track_module('time_bin_bsm')
    log.track_module('optical_channel')
    log.track_module('main_yb_yb_EG_sim')

    total_time = 0

    node0 = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)[0]
    node1 = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)[1]

    node0.meas_fid = 0.99
    node1.meas_fid = 0.99

    app0,_ = RequestApp(node0),RequestApp(node1)

    # TODO remeber why there is the + 1_000_000
    start_time = network_topo.get_cchannels()[4].delay + network_topo.get_cchannels()[5].delay + 1_000_000

    mem0 = node0.get_components_by_type(MemoryArray)[0].memories[0]
    mem1 = node1.get_components_by_type(MemoryArray)[0].memories[0]
    
    mem0.efficiency = photon_collection_efficiency
    mem1.efficiency = photon_collection_efficiency
    mem0.original_memory_efficiency = photon_collection_efficiency
    mem1.original_memory_efficiency = photon_collection_efficiency
    mem0.change_wavelength(wavelength)
    mem1.change_wavelength(wavelength)
    mem0.time_to_retrap = retrap_time
    mem0.time_to_retrap = retrap_time

    for i in range(2):
        qfc = network_topo.qfcs[i]
        qfc.input_wvln = wavelength
        qfc.output_wvln = bsm_operating_wavelength
        qfc.efficiency = qfc_eff
        qfc.dark_count = qfc_dc
        qfc.bin_separation = mem0.bin_separation

    for i in range(n):
        if i == 0:
            node0.basis = "X"
            node1.basis = "X"
        elif int(i/2) == int((i-1)/2):
            node0.basis = "Z"
            node1.basis = "Z"
        else:
            node0.basis = "X"
            node1.basis = "X"
        beginning = tl.now()
        starting_attempts = node0.attempts
        node0.last_trap_time = beginning - node0.time_in_trap
        node1.last_trap_time = beginning - node1.time_in_trap
        tl.init()
        app0.start("router_1", beginning + start_time, beginning + 1_000_000_000_000_000_000, 1, 1)
        log.logger.warning("Starting EG attempt at " + str(tl.time) + '.')
        tl.run()

        taken_time = node1.entanglement_time - beginning
        finishing_attempts = node0.attempts
        traversed_attempts = finishing_attempts - starting_attempts
        net_handshake_time = 31_000_000 + 45_000_000*traversed_attempts # 31us is for rule loading, 45us is for protocol handshakes
        actual_time = (taken_time - net_handshake_time)*(10**-12)
        log.logger.warning(f'Entanglement num {i+1} completed in {actual_time} seconds.')
        log.logger.warning(f'Entanglement num {i+1} took {traversed_attempts} attempts.')
        total_time += actual_time



    fid = node1.get_fidelity(n)

    log.logger.warning(f'After {n} entanglement attempts, calculated fidelity is {fid}.')
    log.logger.warning(f'Average ent time is {total_time/n}.')
    log.logger.warning(f'{n} entanglement pairs were generated after {node0.attempts} attempts.')

if __name__ == "__main__":
    main()