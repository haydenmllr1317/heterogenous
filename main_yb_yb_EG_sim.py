'''
This file is to try and do realistic simulation of entanglement generation
between two single-atom yb nodes. We will be using what we believe are realistic
parameters and mapping average time and attempts required to get entanglement as
well as entanglement fidelity.

NOTE: ADD MORE INFO HERE

'''

from sequence.utils import log
from encoding import yb_time_bin
from copy import copy
from yb_router_net_topo import YbRouterNetTopo
from sequence.app.request_app import RequestApp
from math import inf
import argparse
from memory import MemoryArray

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-pce', '--photoncollectionefficiency', type=float, default=0.5, help='efficiency of photon collection into fiber')
    parser.add_argument('-wavelength', '--photonwavelength', type=int, default=1389, help='wavelength of emmitted photons')
    # parser.add_argument('-t_retrap', '--time_to_retrap', type=int, default=40, help="Time atom has been in trap at which we want to retrap (in seconds).") 
    parser.add_argument('-n', '--numtrials', type=int, default=10, help="number of entangled pairs we generated")
    parser.add_argument('-dtctor_dc', '--detectordarkcount', type=float, default=0.0, help="Dark count rate, in Hz, for the detector in the BSM.")
    parser.add_argument('-dtctor_eff', '--detectorefficiency', type=float, default=0.85, help="Efficiency for the detector in the BSM.") # default should be 0.85 according to Joaquin
    parser.add_argument('-dtctor_res', '--detectorresolution', type=int, default=50_000, help='Minimum time difference our SNSPDs can resolve.')
    parser.add_argument('-bsm_wvln', '--bsm_operating_wavelength', type=int, default=746, help="Photon wavelength BSM ideally operates at.")
    parser.add_argument('-qfc_eff', '--qfc_efficiency', type=float, default=0.5, help="Efficiency of our quantum frequency converters.")
    parser.add_argument('-qfc_noise', '--qfc_noise', type=float, default=0.0, help="Noise, in number of noise photons per signal photon, in our QFC.")

    # take all of our args and make variables of them
    args = parser.parse_args()
    photon_collection_efficiency = args.photoncollectionefficiency
    wavelength = args.photonwavelength
    # lifetime_reload_time= args.time_to_retrap * 1e12
    n = args.numtrials
    detector_dark_count = args.detectordarkcount
    detector_efficiency = args.detectorefficiency
    detector_time_resolution = args.detectorresolution
    bsm_operating_wavelength = args.bsm_operating_wavelength
    qfc_eff = args.qfc_efficiency
    qfc_noise = args.qfc_noise

    # network topology json reference and build
    network_config = 'linear.json'
    network_topo = YbRouterNetTopo(network_config)

    tl = network_topo.get_timeline()
    bsm_hardware_name = 'HetTimeBinBSM' # NOTE Is there a better way to do this?

    bsm_node = network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE)[0]

    # use harware name to grab encoding-appropriate BSM object
    bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]

    # set detector params
    bsm.update_detectors_params('efficiency', detector_efficiency)
    bsm.update_detectors_params('dark_count', detector_dark_count)
    bsm.update_detectors_params('resolution', detector_time_resolution)

    # set params for QFCs
    qfc0 = bsm_node.get_components_by_type("QFC")[0]
    qfc0.input_wvln = wavelength
    qfc0.output_wvln = bsm_operating_wavelength # TODO make this come out of the json file
    qfc0.efficiency = qfc_eff
    qfc0.noise = qfc_noise
    qfc1 = bsm_node.get_components_by_type("QFC")[1]
    qfc1.input_wvln = wavelength
    qfc1.output_wvln = bsm_operating_wavelength # TODO make this come out of the json file
    qfc1.efficiency = qfc_eff
    qfc1.noise = qfc_noise


    #### logging added here ####
    # log_filename = f'pce={photon_collection_efficiency},lambda={wavelength},num_trials={n}.log'
    # log_filename = f'data/fid(qfc_noise)/qfc_noise={qfc_noise}.log'
    log_filename = 'checking.log'
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
    #############################

    total_time = 0 # variable to track total simulation time to get n entanglement paris

    # setting node params
    node0 = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[0]
    node1 = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[1]
    node0.meas_fid = 0.99
    node1.meas_fid = 0.99

    # creating request app
    app0,_ = RequestApp(node0),RequestApp(node1)

    # TODO do RequestApp's need start time?
    start_time = network_topo.get_cchannels()[4].delay + network_topo.get_cchannels()[5].delay

    # grab memories
    mem0 = node0.get_components_by_type(MemoryArray)[0].memories[0] # TODO FIGURE OUT WHY THIS DIDN"T WORK
    mem1 = node1.get_components_by_type(MemoryArray)[0].memories[0]
    
    # set memory parameters
    mem0.efficiency = photon_collection_efficiency
    mem1.efficiency = photon_collection_efficiency
    mem0.original_memory_efficiency = photon_collection_efficiency
    mem1.original_memory_efficiency = photon_collection_efficiency
    mem0.set_wavelength(wavelength)
    mem1.set_wavelength(wavelength)
    # mem0.lifetime_reload_time = lifetime_reload_time
    # mem1.lifetime_reload_time = lifetime_reload_time

    if mem0.bin_width == mem1.bin_width: # Yb nodes must have same bin width
        bsm.bin_width = mem0.bin_width # BSM object needs bin width to know the valid range of trigger times (tolerance)
    else:
        raise ValueError(f'Memory must operate with same bin size, yet mem0={mem0.bin_width} and mem1 = {mem1.bin_width}')
    
    if mem0.bin_separation == mem1.bin_separation: # Yb nodes must have same bin separation
        bsm.time_bin_separation = mem0.bin_separation # BSM objects need to know bin separation to understand valid temporal click distances
    else:
        raise ValueError(f'Memory must operate with same bin separation, yet mem0={mem0.bin_separation} and mem1 = {mem1.bin_separation}')

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
        node0.last_trap_time = beginning - node0.time_in_trap # sets last time of trapping to time_in_trap before current time
        node1.last_trap_time = beginning - node1.time_in_trap # sets last time of trapping to time_in_trap before current time
        tl.init()
        app0.start("router_1", beginning + start_time, beginning + 1_000_000_000_000_000, 1, 1)
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

    # logging
    log.logger.warning(f'After {n} entanglement attempts, calculated fidelity is {fid}.')
    log.logger.warning(f'Average ent time is {total_time/n}.')
    log.logger.warning(f'{n} entanglement pairs were generated after {node0.attempts} attempts.')

if __name__ == "__main__":
    main()