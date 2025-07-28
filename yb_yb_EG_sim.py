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
from generation import EntanglementGenerationTimeBinYb1389, EntanglementGenerationTimeBinYb556
from sequence.message import Message
from sequence.utils import log
import plotly.graph_objects as go
from encoding import yb_time_bin
from copy import copy
from yb_router_net_topo import RouterNetTopo
from request_app import RequestApp
from math import inf



ent = False

# class SimpleManagerYb:
#     def __init__(self, owner, memo_name, encoding):
#         self.owner = owner
#         self.memo_name = memo_name
#         self.raw_counter = 0
#         self.encoding = encoding

#     def update(self, protocol, memory, state):
#         global ent
#         if state == 'RAW':
#             self.raw_counter += 1
#             memory.reset()
#         else:
#             ent = True

#     def create_protocol(self, middle: str, other: str):
#             self.owner.protocols = [EntanglementGenerationTimeBin(self.owner, '%s.eg' % self.owner.name, middle, other, 
#                                                             self.owner.components[self.memo_name], self.encoding, True)]
            
# class for the two nodes that contain the memories we seek to entangle
# class EntangleGenNodeTimeBin(Node):
#     def __init__(self, name: str, tl: Timeline, encoding):
#         super().__init__(name, tl)

#         memo_name = '%s.memo' % name
#         memory = Memory(memo_name, tl, 0.9, 2000, float(23/128), -1, 500)
#         memory.add_receiver(self)
#         self.add_component(memory)
#         self.encoding = encoding

#         self.resource_manager = SimpleManagerYb(self, memo_name, self.encoding)

#     def init(self):
#         memory = self.get_components_by_type("Memory")[0]
#         memory.reset()

#     def receive_message(self, src: str, msg: "Message") -> None:
#         self.protocols[0].received_message(src, msg)

#     def get(self, photon, **kwargs):
#         self.send_qubit(kwargs['dst'], photon)

# pairing protocol, same as example1

# def pair_protocol(node1: Node, node2: Node):
#     p1 = node1.protocols[0]
#     p2 = node2.protocols[0]
#     node1_memo_name = node1.get_components_by_type("Memory")[0].name
#     node2_memo_name = node2.get_components_by_type("Memory")[0].name
#     p1.set_others(p2.name, node2.name, [node2_memo_name])
#     p2.set_others(p1.name, node1.name, [node1_memo_name])


yb_enc = copy(yb_time_bin)

network_config = 'linear.json'
network_topo = RouterNetTopo(network_config)
routers = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
# for router in routers:
#     router.network_manager.
tl = network_topo.get_timeline()

# for router in network_topo.get_nodes_by_type(RouterNetTopoYb.QUANTUM_ROUTER):
#     rm = SimpleManagerYb(router, router.memory_array.memories[0].name, yb_enc)
#     router.set_resource_manager(rm)
#     app = RequestApp(router)


# need a components dictionary so BSMNode can retrieve the encoding_type
# comp_temp = {'encoding_type': 'yb_time_bin'} # should be yb_time_bin
encoding_name = 'TimeBinBSM'

# node1 = EntangleGenNodeTimeBin('node1', tl, yb_enc)
# node2 = EntangleGenNodeTimeBin('node2', tl, yb_enc)

# create our BSMNode object (it creates TimeBinBSM object based on comp_temp)
# bsm_node = BSMNode('bsm_node', tl, ['node1', 'node2'], yb_enc)

# node1.set_seed(0)
# node2.set_seed(1)
# bsm_node.set_seed(2)

# use encoding_name to grab encoding-appropriate BSM object
bsm = network_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)[0].get_components_by_type(encoding_name)[0]
bsm.update_detectors_params('efficiency', 0.85) # accordint to Joaquin should be .85
bsm.update_detectors_params('dark_count', float(11))

# according to Covey paper, attenuation = .3dB/km
# qc1 = QuantumChannel('qc1', tl, attenuation=0.0003, distance=1000)
# qc2 = QuantumChannel('qc2', tl, attenuation=0.0003, distance=1000)
# qc1.set_ends(node1, bsm_node.name)
# qc2.set_ends(node2, bsm_node.name)

# nodes = [node1, node2, bsm_node]

# for i in range(3):
#     for j in range(3):
#         if i != j:
#             log.logger.info('Classical Channel between nodes ' + str(i) + ' and ' + str(j) + ' created.')
#             cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl, 1000, 1e8)
#             cc.set_ends(nodes[i], nodes[j].name)

# logging added here
log_filename = 'yb_yb_EG_sim.log'
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
log.track_module('yb_yb_EG_sim')


rounds_dict = {}
time_dict = {}
running_total = 0
running_time = 0

n = 100

node0 = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)[0]
node1 = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)[1]

app0 = RequestApp(node0)
app1 = RequestApp(node1)

start_time = network_topo.get_cchannels()[4].delay + network_topo.get_cchannels()[5].delay + 1000000

for i in range(n):
    beginning = tl.now()
    print(beginning)
    tl.init()
    app0.start("router_1", beginning + start_time, beginning + 1000000000000, 1, 1)
    log.logger.warning("Starting EG attempt at " + str(tl.time) + '.')
    tl.run()
    print(tl.time)

# # run
# for i in range(n):
#     ent = False



#     node0.resource_manager.raw_counter = 0
#     node1.resource_manager.raw_counter = 0



#     pair_protocol(node1, node2)
#     memoryarray1 = node1.get_components_by_type("MemoryArray")[0]
#     memoryarray1.memories[0].reset()
#     memoryarray2 = node2.get_components_by_type("Memory")[0]
#     memoryarray2.memories[0].reset()
#     node1.protocols[0].start()
#     node2.protocols[0].start()

#     while (not ent):
#         tl.run()
#     ending = tl.now()
#     passed_time = ending - beginning
#     running_time += passed_time
#     try: time_dict[int(running_time)] += 1
#     except: time_dict[int(running_time)] = 1
#     # print('we made it through one run')
#     x = node1.resource_manager.raw_counter
#     try: rounds_dict[x] += 1
#     except: rounds_dict[x] = 1
#     running_total += x

# avg = float(running_total) / float(n)
# avg_time = float(running_time)/float(n)

# print(avg)
# print(avg_time)
# print(avg_time*(10**(-12)))