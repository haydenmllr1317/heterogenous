'''
This file is to try and do realistic simulation of entanglement generation
for a Yb-uW link. We will be using what we believe are realistic
parameters and mapping average time and attempts required to get entanglement as
well as entanglement fidelity.

NOTE: ADD MORE INFO HERE

'''

### MAKE SURE TO KEEP CHANNEL ATTENUTATION IN JSON UPDATED
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
from apps import HetRequestApp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-pce', '--photoncollectionefficiency', type=float, default=0.5, help='efficiency of photon collection into fiber')
    parser.add_argument('-ybwavelength', '--ybphotonwavelength', type=int, default=1389, help='wavelength of emmitted photons from Yb atom')
    parser.add_argument('-n', '--numtrials', type=int, default=1000, help="number of entangled pairs we generated")
    parser.add_argument('-dtctor_dc', '--detectordarkcount', type=float, default=11.0, help="Dark count rate, in Hz, for the detector in the BSM.")
    parser.add_argument('-dtctor_eff', '--detectorefficiency', type=float, default=0.85, help="Efficiency for the detector in the BSM.") # default should be 0.85 according to Joaquin
    parser.add_argument('-bsm_wvln', '--bsm_operating_wavelength', type=int, default=746, help="Photon wavelength BSM ideally operates at.")
    parser.add_argument('-qfc_eff', '--qfc_efficiency', type=float, default=0.99, help="Efficiency of our quantum frequency converters.")
    parser.add_argument('-qfc_noise', '--qfc_noise', type=float, default=0.005, help="Noise, in number of noise photons per signal photon, in our QFC.")
    parser.add_argument('-uw_noise', '--transducer_noise', type=float, default=0.047, help="Noise, in number of photons added to signal during MO transduction.")
    parser.add_argument('-uw_efficiency', '--transducer_efficiency', type=float, default=0.6, help= "Efficiency of uW node, aka probability signal gets converted.")
    parser.add_argument('-uw_coherence', '--transmon_coherence_time', type=int, default=500_000_000, help= "T1 coherence time of transmon.")

    # take all of our args and make variables of them
    args = parser.parse_args()
    photon_collection_efficiency = args.photoncollectionefficiency
    yb_wavelength = args.ybphotonwavelength
    n = args.numtrials
    detector_dark_count = args.detectordarkcount
    detector_efficiency = args.detectorefficiency
    bsm_operating_wavelength = args.bsm_operating_wavelength
    qfc_eff = args.qfc_efficiency
    qfc_noise = args.qfc_noise
    uW_noise = args.transducer_noise
    uW_efficiency = args.transducer_efficiency
    transmon_coherence = args.transmon_coherence_time

    # network topology json reference and build
    network_config = 'config/linear_het.json'
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
        qfc0.input_wvln = yb_wavelength
        qfc0.output_wvln = bsm_operating_wavelength # TODO make this come out of the json file
        qfc0.efficiency = qfc_eff
        qfc0.noise = qfc_noise
        qfc1 = bsm_node.get_components_by_type("QFC")[1]
        qfc1.input_wvln = 1389
        qfc1.output_wvln = bsm_operating_wavelength # TODO make this come out of the json file
        qfc1.efficiency = qfc_eff
        qfc1.noise = qfc_noise


    #### logging added here ####
    log_filename = f'tmp/data/qfc_noise/qfc_noise={qfc_noise}.log'
    # log_filename = f'tmp/data/qfc_eff/qfc_eff={qfc_eff}.log'
    # log_filename = f'tmp/data/uw_eff/uw_eff={uW_efficiency}.log'
    # log_filename = f'tmp/data/uw_noise/uw_noise={uW_noise}.log'
    # log_filename = f'tmp/data/coherence/coherence={transmon_coherence}.log'
    # log_filename = 'tmp/checking_het.log'
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('WARNING')
    log.track_module('main_yb_uW_EG_sim')
    log.track_module('generation')
    log.track_module('bsm')
    log.track_module('detector')
    log.track_module('memory')
    log.track_module('photon')
    log.track_module('custom_node')
    log.track_module('time_bin_bsm')
    log.track_module('optical_channel')
    log.track_module('main_yb_yb_EG_sim')
    log.track_module('apps')
    #############################

    total_time = 0 # variable to track total simulation time to get n entanglement paris

    name_to_app = {}

    # setting node params
    for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
        name_to_app[node.name] = HetRequestApp(node)
        if node.memo_type == "Yb":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.efficiency = photon_collection_efficiency
                mem.original_memory_efficiency = photon_collection_efficiency
                mem.set_wavelength(yb_wavelength)
        elif node.memo_type == "uW":
            for mem in node.get_components_by_type(MemoryArray)[0].memories:
                mem.transducer_efficiency = uW_efficiency
                mem.transducer_noise = uW_noise
                mem.set_wavelength = 10 # 10Ghz, just left this value here
                mem.coherence_time = transmon_coherence
        else:
            raise ValueError("Only funcitonal for uW and Yb memories currently.")

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
            basis = "Z"
            basis = "Z"
        else: # even
            basis = "X"
            basis = "X"
        beginning = tl.now()
        starting_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        for node in network_topo.get_nodes_by_type(YbRouterNetTopo.QUANTUM_ROUTER):
            node.app.last_trap_time = beginning - node.app.time_in_trap # sets last time of trapping to time_in_trap before current time
        name_to_app[node_init.name].start(node_resp.name, beginning + delta, beginning + 10000*SECOND, 1, 0.1, basis) # requesting 1 pair with min fid of 0.1
        name_to_app[node_resp.name].basis = basis
        log.logger.warning("Starting EG attempt at " + str(tl.time) + '.')
        tl.run()

        taken_time = node_init.app.entanglement_time - beginning
        finishing_attempts = node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts
        traversed_attempts = finishing_attempts - starting_attempts
        # net_handshake_time = 31_000_000 + 45_000_000*traversed_attempts # 31us is for rule loading, 45us is for protocol handshakes
        # actual_time = (taken_time - net_handshake_time)*(10**-12)
        actual_time = taken_time*(10**-12)
        if actual_time < 0:
            raise ValueError('neg actual time')
        log.logger.warning(f'Entanglement num {i+1} completed in {actual_time} seconds.')
        log.logger.warning(f'Entanglement num {i+1} took {traversed_attempts} attempts.')
        total_time += actual_time


    readout_fidelity0 = node_init.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    readout_fidelity1 = node_resp.get_components_by_type(MemoryArray)[0].memories[0].measurement_fidelity
    fid = node_init.app.get_fidelity(readout_fidelity0*readout_fidelity1)

    # logging
    log.logger.warning(f'qfc noise:{qfc_noise}')
    log.logger.warning(f'After {n} entanglement attempts, calculated fidelity ={fid}')
    log.logger.warning(f'Average ent time is ~{total_time/n}')
    log.logger.warning(f'{n} entanglement pairs were generated after {node_init.get_components_by_type(MemoryArray)[0].memories[0].attempts} attempts.')

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