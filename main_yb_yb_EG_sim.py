'''
This file is to try and do realistic simulation of entanglement generation
between two single-atom yb nodes. We will be using what we believe are realistic
parameters and mapping average time and attempts required to get entanglement.

NOTE: ADD MORE INFO HERE

'''


from sequence.kernel.timeline import Timeline
from custom_node import Node, BSMNode
from memory import Memory
from qchannels import QuantumChannel, ClassicalChannel
from generation import EntanglementGenerationTimeBin
from sequence.message import Message
from sequence.utils import log
# import plotly.graph_objects as go
# import matplotlib.pyplot as plt
from encoding import yb_time_bin
from copy import copy
import argparse
import time

ent = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-eff', '--memoryefficiency', type=float, default=0.5, help='efficiency of quantum memory')
    parser.add_argument('-n', '--numtrials', type=int, default=100, help='number of entanglement pairs to be generated')
    parser.add_argument('-retrap', '--numretrap', type=int, default=128, help='number of entanglement attempts before retrap')
    parser.add_argument('-darkc', '--darkcount', type=int, default=11, help='dark count parameter of detectors')
    args = parser.parse_args()
    mem_eff = args.memoryefficiency
    n = args.numtrials
    retrap_num = args.numretrap
    dark_count = args.darkcount

    global ent

    # 40.44
    # 17.61
    # 8.33

    class SimpleManagerYb:
        def __init__(self, owner, memo_name, encoding):
            self.owner = owner
            self.memo_name = memo_name
            self.raw_counter = 0
            self.encoding = encoding
            self.entangled = False
            self.meas = {0:0, 1:0, 2:0}
            self.x_list = []
            self.y_list = []
            self.z_list = []

        def update(self, protocol, memory, state):
            global ent
            if state == 'RAW':
                self.raw_counter += 1
                memory.reset()
            else:
                ent = True
                self.entangled = True

        def create_protocol(self, middle: str, other: str):
                self.owner.protocols = [EntanglementGenerationTimeBin(self.owner, '%s.eg' % self.owner.name, middle, other, 
                                                                self.owner.components[self.memo_name], self.encoding, True, retrap_num=retrap_num)]
        
        def fid_measurement(self, result: float, basis: int):
            self.meas[basis] += result
            if basis == 0:
                self.x_list.append(result)
            elif basis == 1:
                self.y_list.append(result)
            elif basis == 2:
                self.z_list.append(result)
            if basis == 2:
                if result != -1:
                    print("AHHHH")
                    print(result)
            
                
    # class for the two nodes that contain the memories we seek to entangle
    class EntangleGenNodeTimeBin(Node):
        def __init__(self, name: str, tl: Timeline, encoding):
            super().__init__(name, tl)

            memo_name = '%s.memo' % name
            memory = Memory(memo_name, tl, 1.0, 2000, mem_eff, -1, 500)
            memory.add_receiver(self)
            self.add_component(memory)
            self.encoding = encoding
            self.original_mem_eff = mem_eff
            self.attempts = 0
            self.atom_lost = False

            self.resource_manager = SimpleManagerYb(self, memo_name, self.encoding)

        def init(self):
            memory = self.get_components_by_type("Memory")[0]
            memory.reset()

        def receive_message(self, src: str, msg: "Message") -> None:
            self.protocols[0].received_message(src, msg)

        def get(self, photon, **kwargs):
            self.send_qubit(kwargs['dst'], photon)

    # pairing protocol, same as example1
    def pair_protocol(node1: Node, node2: Node):
        p1 = node1.protocols[0]
        p2 = node2.protocols[0]
        node1_memo_name = node1.get_components_by_type("Memory")[0].name
        node2_memo_name = node2.get_components_by_type("Memory")[0].name
        p1.set_others(p2.name, node2.name, [node2_memo_name])
        p2.set_others(p1.name, node1.name, [node1_memo_name])

    tl = Timeline()

    # need a components dictionary so BSMNode can retrieve the encoding_type
    # comp_temp = {'encoding_type': 'yb_time_bin'} # should be yb_time_bin
    encoding_name = 'TimeBinBSM'

    yb_enc = copy(yb_time_bin)

    node1 = EntangleGenNodeTimeBin('node1', tl, yb_enc)
    node2 = EntangleGenNodeTimeBin('node2', tl, yb_enc)

    # create our BSMNode object (it creates TimeBinBSM object based on comp_temp)
    bsm_node = BSMNode('bsm_node', tl, ['node1', 'node2'], yb_enc)

    node1.set_seed(0)
    node2.set_seed(1)
    bsm_node.set_seed(2)

    # use encoding_name to grab encoding-appropriate BSM object
    bsm = bsm_node.get_components_by_type(encoding_name)[0]
    bsm.update_detectors_params('efficiency', 0.85) # accordint to Covey
    bsm.update_detectors_params('dark_count', float(dark_count))

    # according to Covey paper, attenuation = .3dB/km
    qc1 = QuantumChannel('qc1', tl, attenuation=0.0003, distance=1000) # was 0.0003
    qc2 = QuantumChannel('qc2', tl, attenuation=0.0003, distance=1000)
    qc1.set_ends(node1, bsm_node.name)
    qc2.set_ends(node2, bsm_node.name)

    nodes = [node1, node2, bsm_node]

    for i in range(3):
        for j in range(3):
            if i != j:
                log.logger.info('Classical Channel between nodes ' + str(i) + ' and ' + str(j) + ' created.')
                cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl, 1000, 1e8)
                cc.set_ends(nodes[i], nodes[j].name)

    # logging added here
    # log_filename = f'retrap={retrap_num},mem_eff={mem_eff},num_trials={n}.log'
    log_filename = f'stupid_test2.log'
    # log_filename = 'darkcountsearch.log'
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


    rounds_dict = {}
    time_dict = {}
    running_total = 0
    running_time = 0

    # print('we here')

    start = time.time() 

    # run
    for i in range(n):
        # print('round' + str(i))
        beginning = tl.now()
        tl.init()
        ent = False
        node1.resource_manager.raw_counter = 0
        node2.resource_manager.raw_counter = 0
        node1.resource_manager.create_protocol('bsm_node', 'node2')
        node2.resource_manager.create_protocol('bsm_node', 'node1')
        pair_protocol(node1, node2)
        memory1 = node1.get_components_by_type("Memory")[0]
        memory1.reset()
        memory2 = node2.get_components_by_type("Memory")[0]
        memory2.reset()
        node1.protocols[0].start()
        node2.protocols[0].start()

        # print(memory1.basis)

        while (not ent):
            tl.run()

        for m in [memory1,memory2]:
            if m.basis == 2:
                m.basis = 0
            else:
                m.basis += 1
        
        if memory1.basis != memory2.basis:
            raise ValueError('memories dont agree on measurement basis')

        ending = tl.now()
        passed_time = ending - beginning
        running_time += passed_time
        try: time_dict[int(running_time)] += 1
        except: time_dict[int(running_time)] = 1
        # print('we made it through one run')
        x = node1.resource_manager.raw_counter
        try: rounds_dict[x] += 1
        except: rounds_dict[x] = 1
        running_total += x
        log.logger.warning('Time taken for ent no.' + str(i+1) + ': '+ str(passed_time*(10**(-12))))

    rm = node1.resource_manager
    
    meas_dict = rm.meas
    # print(meas_dict)
    # print(str(meas_dict.keys()))
    # print(str(meas_dict.values()))
    low_bar = int(n/3)
    delta = int(3*((n/3)-low_bar))
    if delta == 1:
        high_bar = low_bar + 1
        mid_bar = low_bar
    elif delta ==2:
        high_bar = low_bar + 1
        mid_bar = high_bar
    elif delta ==0:
        high_bar = low_bar
        mid_bar = low_bar
    fidelity = .999*(1/4)*(1+(-meas_dict[2]/low_bar)+(meas_dict[0]/high_bar)+(meas_dict[1]/mid_bar))
    # print(-meas_dict[2]+meas_dict[0]+meas_dict[1])

    # if fidelity < 0: fidelity = 0
    # elif fidelity > 1: fidelity = 1

    log.logger.warning(f'Total Fidelity was: {fidelity}.')

    # print('fidelity is ' + str(fidelity))

    # print(rm.x_list)
    # print(rm.y_list)
    # print(rm.z_list)

    avg = float(running_total) / float(n)
    avg_time = float(running_time)/float(n)

    over = time.time()
    elapsed_computer = over-start
    log.logger.warning(f'At end, computer took {elapsed_computer:.2f} seconds.')

    # print(avg)
    # print(avg_time)
    # print(avg_time*(10**(-12)))
    log.logger.warning('At end, avg time to ent was ' + str(avg_time*(10**(-12))) + ' seconds.')

if __name__ == '__main__':
    main()