'''
This file is to try and do realistic simulation of entanglement generation
between two single-atom yb nodes. We will be using what we believe are realistic
parameters and mapping average time and attempts required to get entanglement as
well as entanglement fidelity.

NOTE: ADD MORE INFO HERE

'''

#### REMEMBER I CHANGED THE QCHANNEL ATTENUTATION IN JSON
####  ALSO COMMENTED OUT THE ATOM BRANCHING RATIOS, DEPUMPING LOSS, and LATE DECAY PROBABILITY WITHIN MEMORY

from sequence.utils import log
from encoding import yb_time_bin
from copy import copy
from yb_router_net_topo import YbRouterNetTopo
from sequence.app.request_app import RequestApp
from math import inf
import argparse
from memory import MemoryArray
from sequence.constants import MILLISECOND, SECOND

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-pce', '--photoncollectionefficiency', type=float, default=1.0, help='efficiency of photon collection into fiber')
    parser.add_argument('-wavelength', '--photonwavelength', type=int, default=1389, help='wavelength of emmitted photons')
    # parser.add_argument('-t_retrap', '--time_to_retrap', type=int, default=40, help="Time atom has been in trap at which we want to retrap (in seconds).") 
    parser.add_argument('-n', '--numtrials', type=int, default=5000, help="number of entangled pairs we generated")
    parser.add_argument('-dtctor_dc', '--detectordarkcount', type=float, default=0.0, help="Dark count rate, in Hz, for the detector in the BSM.")
    parser.add_argument('-dtctor_eff', '--detectorefficiency', type=float, default=1.0, help="Efficiency for the detector in the BSM.") # default should be 0.85 according to Joaquin
    # parser.add_argument('-dtctor_res', '--detectorresolution', type=int, default=50_000, help='Minimum time difference our SNSPDs can resolve.') NOTE THIS IS NOT WHAT WE WANT, LEAVING CLASS AS IS
    parser.add_argument('-bsm_wvln', '--bsm_operating_wavelength', type=int, default=746, help="Photon wavelength BSM ideally operates at.")
    parser.add_argument('-qfc_eff', '--qfc_efficiency', type=float, default=1.0, help="Efficiency of our quantum frequency converters.")
    parser.add_argument('-qfc_noise', '--qfc_noise', type=float, default=0.02, help="Noise, in number of noise photons per signal photon, in our QFC.")

    # take all of our args and make variables of them
    args = parser.parse_args()
    photon_collection_efficiency = args.photoncollectionefficiency
    wavelength = args.photonwavelength
    # lifetime_reload_time= args.time_to_retrap * 1e12
    n = args.numtrials
    detector_dark_count = args.detectordarkcount
    detector_efficiency = args.detectorefficiency
    # detector_time_resolution = args.detectorresolution # NOTE LEAVING CLASS AS IS FOR NOW
    bsm_operating_wavelength = args.bsm_operating_wavelength
    qfc_eff = args.qfc_efficiency
    qfc_noise = args.qfc_noise

    # network topology json reference and build
    network_config = 'config/linear.json'
    network_topo = YbRouterNetTopo(network_config)

    tl = network_topo.get_timeline()
    bsm_hardware_name = 'HetTimeBinBSM' # NOTE Is there a better way to do this?

    for bsm_node in network_topo.get_nodes_by_type(YbRouterNetTopo.BSM_NODE):
        # use harware name to grab encoding-appropriate BSM object
        bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]

        # set detector params
        bsm.update_detectors_params('efficiency', detector_efficiency)
        bsm.update_detectors_params('dark_count', detector_dark_count)
        # bsm.update_detectors_params('resolution', detector_time_resolution) # NOTE LEAVING CLASS AS IS, DONT NEED TO CHANGE RESOLUTION

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
    log_filename = f'tmp/data/fid(qfc_noise)/qfc_noise={qfc_noise}.log'
    # log_filename = 'tmp/checking.log'
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('WARNING')
    log.track_module('main_yb_yb_EG_sim')
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

    name_to_app = {}

    # setting node params
    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = RequestApp(node)
        node.meas_fid = 0.99 # TODO include this in the JSON file so it's initialized
        for mem in node.get_components_by_type(MemoryArray)[0].memories:
            mem.efficiency = photon_collection_efficiency
            mem.original_memory_efficiency = photon_collection_efficiency
            mem.set_wavelength(wavelength)
        memory = node.get_components_by_type(MemoryArray)[0].memories[0]
        for bsm_node_name in node.qchannels.keys():
            bsm_node = tl.get_entity_by_name(bsm_node_name)
            bsm = bsm_node.get_components_by_type(bsm_hardware_name)[0]
            bsm.bin_width = max(memory.bin_width, bsm.bin_width)
            bsm.bin_separation = max(memory.bin_separation, bsm.bin_separation)

            # mem.lifetime_reload_time = lifetime_reload_time

    # start_time = network_topo.get_cchannels()[4].delay + network_topo.get_cchannels()[5].delay

    delta = 20*MILLISECOND

    tl.init()

    # TEMPORARY SOLUTION
    node_init = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[0]
    node_resp = network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER)[1]
    

    for i in range(n):
        if i%2 == 1: # odd
            node_init.basis = "Z"
            node_resp.basis = "Z"
        else: # even
            node_init.basis = "X"
            node_resp.basis = "X"
        beginning = tl.now()
        starting_attempts = node_init.attempts
        node_init.last_trap_time = beginning - node_init.time_in_trap # sets last time of trapping to time_in_trap before current time
        node_resp.last_trap_time = beginning - node_resp.time_in_trap # sets last time of trapping to time_in_trap before current time
        name_to_app[node_init.name].start(node_resp.name, beginning + delta, beginning + 1*SECOND, 1, 1)
        log.logger.warning("Starting EG attempt at " + str(tl.time) + '.')
        tl.run()
        if node_init.name > node_resp.name:
            taken_time = node_init.entanglement_time - beginning
        else:
            taken_time = node_resp.entanglement_time - beginning
        finishing_attempts = node_init.attempts
        traversed_attempts = finishing_attempts - starting_attempts
        # net_handshake_time = 31_000_000 + 45_000_000*traversed_attempts # 31us is for rule loading, 45us is for protocol handshakes
        # actual_time = (taken_time - net_handshake_time)*(10**-12)
        actual_time = taken_time*(10**-12)
        log.logger.warning(f'Entanglement num {i+1} completed in {actual_time} seconds.')
        log.logger.warning(f'Entanglement num {i+1} took {traversed_attempts} attempts.')
        total_time += actual_time

    fid = node_resp.get_fidelity()

    # logging
    log.logger.warning(f'QFC noise:{qfc_noise}')
    log.logger.warning(f'After {n} entanglement attempts, calculated fidelity ={fid}')
    log.logger.warning(f'Average ent time is {total_time/n}.')
    log.logger.warning(f'{n} entanglement pairs were generated after {node_init.attempts} attempts.')

    # print(bsm_node.conversion_counter)
    # print(bsm_node.qfc_noise_counter)
    # print(bsm_node.noise_to_detector)
    # print(bsm_node.detectors_got)
    # print(bsm_node.detectors_recorded)
    # print(bsm.detectors[0].undetectable_photon_count + bsm.detectors[1].undetectable_photon_count)
    # print(bsm_node.trigger_sent)
    # print('new')
    # print(node0.ll)
    # print(node1.ll)

if __name__ == "__main__":
    main()