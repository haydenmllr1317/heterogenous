'''
This file is an example of using time-bin photons for a single-heralded
entanglement protocol between two quantum memories.

This file follows 'example1' found in Chapter 3 of the SeQUeNCe
tutorial here: /SeQUeNCe/docs/source/tutorial/chapter3/example1.py
but is modified to handle time_bin instead of single_atom encoded photons.

This is done with the intention of beginning to build infrastructure
for modelling the Yb atom computer as a node in a quantum network. The
Yb computer will emmit photons we will view as time_bin encoded.

'''
from sequence.kernel.timeline import Timeline
from custom_node import Node, BSMNode
from memory import Memory
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from generation import EntanglementGenerationTimeBin
from sequence.message import Message
from sequence.utils import log

# basic manager to get the state of memory after protocols
# exact same as in example1, except we instead create the
#   EngtanglementGenerationTimeBin protocol
class SimpleManager:
    def __init__(self, owner, memo_name):
        self.owner = owner
        self.memo_name = memo_name
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
            memory.reset()
        else:
            self.ent_counter += 1

    def create_protocol(self, middle: str, other: str):
            self.owner.protocols = [EntanglementGenerationTimeBin(self.owner, '%s.eg' % self.owner.name, middle, other, 
                                                            self.owner.components[self.memo_name])]

# class for the two nodes that contain the memories we seek to entangle
# it's the exact same as in example1
class EntangleGenNodeTimeBin(Node):
    def __init__(self, name: str, tl: Timeline):
        super().__init__(name, tl)

        memo_name = '%s.memo' % name
        memory = Memory(memo_name, tl, 0.9, 2000, 1, -1, 500) # NOTE: change params!!!
                # params in order:
                #   initial fidelity of memory
                #   maximum freq of excitation for memory
                #   coherance time (avg time in s)
                #   decoherance rate rate of decoherance
                #   wavelength of photons emmitted (in nm)
        memory.add_receiver(self)
        self.add_component(memory)

        self.resource_manager = SimpleManager(self, memo_name)

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
comp_temp = {'encoding_type': 'time_bin'}
encoding_name = 'TimeBinBSM'

node1 = EntangleGenNodeTimeBin('node1', tl)
node2 = EntangleGenNodeTimeBin('node2', tl)

# create our BSMNode object (it creates TimeBinBSM object based on comp_temp)
bsm_node = BSMNode('bsm_node', tl, ['node1', 'node2'], component_templates = comp_temp)

node1.set_seed(0)
node2.set_seed(1)
bsm_node.set_seed(2)

# use encoding_name to grab encoding-appropriate BSM object
bsm = bsm_node.get_components_by_type(encoding_name)[0]
bsm.update_detectors_params('efficiency', 1) # whatever this should be

qc1 = QuantumChannel('qc1', tl, attenuation=0, distance=1000) # distance in m
qc2 = QuantumChannel('qc2', tl, attenuation=0, distance=1000)
qc1.set_ends(node1, bsm_node.name)
qc2.set_ends(node2, bsm_node.name)

nodes = [node1, node2, bsm_node]

for i in range(3):
    for j in range(3):
        if i != j:
            log.logger.info('Classical Channel between nodes ' + str(i) + ' and ' + str(j) + ' created.')
            cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl, 1000, 1e8) #distance in m
            cc.set_ends(nodes[i], nodes[j].name)


# logging added here
log_filename = 'time_bin_entangle_ex.log'
log.set_logger(__name__, tl, log_filename)
log.set_logger_level('DEBUG')
log.track_module('generation')
log.track_module('bsm')
log.track_module('detector')
log.track_module('memory')
log.track_module('photon')
log.track_module('node')
log.track_module('time_bin_bsm')


# run
for i in range(1000):
    # tl.time = tl.now() + 1e11
    node1.resource_manager.create_protocol('bsm_node', 'node2')
    node2.resource_manager.create_protocol('bsm_node', 'node1')
    pair_protocol(node1, node2)

    memory1 = node1.get_components_by_type("Memory")[0]
    memory1.reset()
    memory2 = node2.get_components_by_type("Memory")[0]
    memory2.reset()

    node1.protocols[0].start()
    node2.protocols[0].start()
    tl.run()

print("node1 entangled memories : available memories")
print(node1.resource_manager.ent_counter, ':', node1.resource_manager.raw_counter)
print('photon measurement distribution, e = early, l = late:')
print("ee:el:le:ll")
print(bsm_node.components['bsm_node.BSM'].early_early, ":",
      bsm_node.components['bsm_node.BSM'].early_late, ":",
      bsm_node.components['bsm_node.BSM'].late_early, ":",
      bsm_node.components['bsm_node.BSM'].late_late)

# the following counters are explained in time_bin_bsm file
print('total triggered: ' + str(bsm_node.components['bsm_node.BSM'].trigger_count))
print('appropriate time photon count: ' + str(bsm_node.components['bsm_node.BSM'].appropriate_time_photon_count))
print('appropriate state, invalid time, photon count: ' + str(bsm_node.components['bsm_node.BSM'].approved_state_invalid_time_photon_count))
print('invalid photon count: ' + str(bsm_node.components['bsm_node.BSM'].invalid_state_photon_count))

# the following counters are explained in detector file
print('total photons in detector 1: ' + str(bsm_node.components['bsm_node.BSM'].detectors[0].photon_counter))
print('total photons in detector 2: ' + str(bsm_node.components['bsm_node.BSM'].detectors[1].photon_counter))
print('total photons recorded in detector 1: ' + str(bsm_node.components['bsm_node.BSM'].detectors[0].recorded_detection_count))
print('total photons recorded in detector 2: ' + str(bsm_node.components['bsm_node.BSM'].detectors[1].recorded_detection_count))
print('total photons undetectable in detector 1: ' + str(bsm_node.components['bsm_node.BSM'].detectors[0].undetectable_photon_count))
print('total photons undetectable in detector 2: ' + str(bsm_node.components['bsm_node.BSM'].detectors[1].undetectable_photon_count))