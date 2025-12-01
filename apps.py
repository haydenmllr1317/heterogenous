from sequence.app.request_app import RequestApp
from sequence.resource_management.memory_manager import MemoryInfo
from sequence.components.memory import Memory
from sequence.utils import log
from math import sqrt
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from math import e
from memory import _set_state_with_fidelity

class HetRequestApp(RequestApp):

    _psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]
    _psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]


    def __init__(self, node):
        self.basis = None
        self.meas_results = {"X_11": 0, "X_22": 0, "X_33": 0, "X_44": 0, "Z_11": 0, "Z_22": 0, "Z_33": 0, "Z_44": 0}
        self.entanglement_time = None
        self.attempts = 0
        self.last_trap_time = 0
        self.time_in_trap = 0
        super().__init__(node)

    def start(self, responder: str, start_t: int, end_t: int, memo_size: int, fidelity: float, basis: str):
        self.basis = basis
        super().start(responder, start_t, end_t, memo_size, fidelity)

    def get_memory(self, info: MemoryInfo) -> None:
        """Method to receive entangled memories.

        Will check if the received memory is qualified.
        If it's a qualified memory, the application sets memory to RAW state
        and release back to resource manager.
        The counter of entanglement memories, 'memory_counter', is added.
        Otherwise, the application does not modify the state of memory and
        release back to the resource manager.

        Args:
            info (MemoryInfo): info on the qualified entangled memory.
        """

        if info.state != "ENTANGLED":
            return
        
        other_memory = self.node.timeline.get_entity_by_name(info.remote_memo)
        
        time_to_measurement_results = self.node.timeline.now() + max(info.memory.measurement_time, other_memory.measurement_time) # current time + time it takes to measure

        if self.basis == "X":
            to_x_basis_time = max(info.memory.to_x_basis_time, other_memory.to_x_basis_time)
            time_to_measurement_results +=  to_x_basis_time

        self.time_in_trap = time_to_measurement_results - self.last_trap_time


        if info.index in self.memo_to_reservation:

            if self.node.memo_type == "uW":
                time_since_excite = self.node.timeline.now() - info.memory.time_after_excitement
                if self.basis == "X":
                    readout_time = info.memory.measurement_time + info.memory.to_x_basis_time
                else:
                    readout_time = info.memory.measurement_time
                time_since_excite += readout_time
                decohere_prob = (1-e**(-time_since_excite/info.memory.coherence_time))
                if self.node.get_generator().random() < decohere_prob: # decohered during roundtrip time
                    log.logger.warning('Transmon decohered during round trip time.')
                    qm = self.node.timeline.quantum_manager
                    info.memory.update_state(info.memory._zero_ket)
                    other_memory.update_state(other_memory._zero_ket)
                    # if self.basis == "X":
                    #     if info.memory.psi_sign == 1:
                    #         _set_state_with_fidelity([info.memory.qstate_key, other_memory.qstate_key], self._psi_minus, 1.0, self.node.get_generator(), qm) # NOTE hardcoded fidelity to 1.0
                    #     elif info.memory.psi_sign == -1:
                    #         _set_state_with_fidelity([info.memory.qstate_key, other_memory.qstate_key], self._psi_plus, 1.0, self.node.get_generator(), qm) # NOTE hardcoded fidelity to 1.0
                    # elif self.basis == "Z": 
                    #     info.memory.update_state(info.memory._zero_ket)
                    #     other_memory.update_state(other_memory._zero_ket)

            reservation = self.memo_to_reservation[info.index]
            if info.remote_node == reservation.initiator and info.fidelity >= reservation.fidelity:
                pass
                # process = Process(self.node.resource_manager, 'update', [None, info.memory, "RAW"])
                # event = Event(time_to_measurement_results, process)
                # self.node.timeline.schedule(event)
            elif info.remote_node == reservation.responder and info.fidelity >= reservation.fidelity:
                self.memory_counter += 1
                log.logger.info(f"Successfully generated entanglement. Counter is at {self.memory_counter}.")
                remote_memory_key = other_memory.qstate_key

                process = Process(self, 'measure_and_save', [info.memory, remote_memory_key])
                event = Event(time_to_measurement_results, process)
                self.node.timeline.schedule(event)

    def measure_and_save(self, memory, remote_memory_key):

        measurement = memory.measure(remote_memory_key)

        # psi_sign is 1 for psi+ and -1 for psi-
        # measurement is length 2 list where each element is 0 (down) or 1 (up)

        # for PSI- we want to flip the sign of X_same and X_diff in our Fidelity formula
        # to do that, I am just flipping X_same and X_diff right here as they have opposite signs in the formula
        if memory.psi_sign == -1 and self.basis == "X":
            if measurement[0] == 0:
                measurement[0] = 1
            elif measurement[0] == 1:
                measurement[0] = 0
            else:
                raise ValueError(f'Measurement result should be a bit, not {measurement[0]}')

        if measurement[0] == measurement[1] == 0: # \rho_11 in either basis
            self.meas_results[self.basis + '_11'] += 1
        elif measurement[0] == measurement[1] == 1: # \rho_44 in either basis
            self.meas_results[self.basis + '_44'] += 1
        elif (measurement[0] == 0) and (measurement[1] == 1): # \rho_22 in either basis
            self.meas_results[self.basis + '_22'] += 1
        elif (measurement[0] == 1) and (measurement[1] == 0): # \rho_33 in either basis
            self.meas_results[self.basis + '_33'] += 1
        else:
            raise ValueError(f'Measurement values should both be bits, not {measurement}.')

        self.entanglement_time = self.node.timeline.now()

        # remove detector dark counts so we can finish simulation as we have succesfully heralded entanglement
        for event in self.node.timeline.events:
            if event.process.activation in ['add_dark_count', 'record_detection', 'lose_atom']:
                self.node.timeline.remove_event(event)
        # print('try')


    def get_fidelity(self, meas_fid):
        # fidelity calculation derived from:
        # https://static-content.springer.com/esm/art%3A10.1038%2Fnature12016/MediaObjects/41586_2013_BFnature12016_MOESM10_ESM.pdf
        # which is in supplementary information of this paper:
        # https://www.nature.com/articles/nature12016#Sec2

        # told measurements in X and Z bases respectively
        X_trials = sum(self.meas_results[f'X_{i}{i}'] for i in range(1,5))
        Z_trials = sum(self.meas_results[f'Z_{i}{i}'] for i in range(1,5))

        rhoX_diff = (self.meas_results[f'X_22']+self.meas_results[f'X_33'])/X_trials
        rhoX_same = (self.meas_results[f'X_11']+self.meas_results[f'X_44'])/X_trials
        rhoZ_diff = (self.meas_results[f'Z_22']+self.meas_results[f'Z_33'])/Z_trials # rho_22 + rho_33
        rhoZ_prod_same = (self.meas_results[f'Z_11']/Z_trials)*(self.meas_results[f'Z_44']/Z_trials) # rho_11*rho_44

        # print(rhoX_diff)
        # print(rhoX_same)
        # print(rhoZ_diff)
        # print(rhoZ_prod_same)

        f = meas_fid * (rhoZ_diff + rhoX_same - rhoX_diff - 2*sqrt(rhoZ_prod_same))/2
        return f

        