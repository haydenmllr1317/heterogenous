import matplotlib.pyplot as plt
import re
import glob

log_files = glob.glob("retrap=*.log")

trap_freqs = []
times_to_ent = []


for filename in log_files:
    retrap = None
    ent_time = None
    retrap_match = re.search(r"retrap=([\d.]+)", filename)
    if retrap_match:
        retrap = retrap_match.group(1)
    with open(filename, 'r') as f:
        for line in f:
            ent_time_match = re.search(r"At end, avg time to ent was (\d+\.\d+)", line)
            if ent_time_match:
                ent_time = float(ent_time_match.group(1))
                break
    trap_freqs.append(int(retrap))
    times_to_ent.append(ent_time)
    

sorted_pairs = sorted(zip(trap_freqs, times_to_ent))
x_sorted, y_sorted = zip(*sorted_pairs)

freqs_sorted = list(x_sorted)
times_sorted = list(y_sorted)

print(freqs_sorted)
print(times_sorted)

plt.figure()
plt.plot(freqs_sorted, times_sorted, marker='o')
plt.xlabel("Attempts Per Sequence")
plt.ylabel("Simulation Time per Ent Pair (s)")
plt.title("Entanglement Generation Time Given Sequence Attempts")
plt.grid(True)
plt.savefig('ent_time_from_retrap_times.png')
# plt.show()


# old plots
# compute_mem_eff = []
# compute_times = []

# sim_mem_eff = []
# sim_times = []

# for filename in log_files:
#     mem_eff = None
#     num_trials = None
#     mem_match = re.search(r"mem_eff=([\d.]+)", filename)
#     if mem_match:
#         mem_eff = mem_match.group(1)
#     n_match = re.search(r"num_trials=(\d+)", filename)
#     if n_match:
#         num_trials = int(n_match.group(1))
#     with open(filename, 'r') as f:
#         for line in f:
#             compute_match = re.search(r"At end, computer took (\d+\.\d+) seconds.", line)
#             if compute_match:
#                 compute_mem_eff.append(mem_eff)
#                 compute_times.append(float(compute_match.group(1))/num_trials)
#             sim_match = re.search(r"time to ent was (\d+\.\d+) seconds.", line)
#             if sim_match:
#                 sim_mem_eff.append(mem_eff)
#                 sim_times.append(float(sim_match.group(1)))
#             sim_ent_match = re.search(r"Time taken for ent no.\d+: (\d+\.\d+)", line)



# sorted_pairs = sorted(zip(compute_mem_eff, compute_times))
# x_sorted, y_sorted = zip(*sorted_pairs)

# compute_mem_eff_sorted = list(x_sorted)
# compute_times_sorted = list(y_sorted)

# plt.figure()
# plt.plot(compute_mem_eff_sorted, compute_times_sorted, marker='o')
# plt.xlabel("Memory Efficiency")
# plt.ylabel("Real Compute Time per Ent Pair (s)")
# plt.title("Average Runtime to Generate Entanglement")
# plt.grid(True)
# plt.savefig('compute_time_to_mem_eff.png')

# print(compute_mem_eff_sorted)
# print(compute_times_sorted)

# sim_sorted_pairs = sorted(zip(sim_mem_eff, sim_times))
# sim_x_sorted, sim_y_sorted = zip(*sim_sorted_pairs)

# sim_mem_eff_sorted = list(sim_x_sorted)
# sim_times_sorted = list(sim_y_sorted)

# sim_expected_x = ['0.025', '0.05', '0.1', '0.25', '0.5', '1.0']
# sim_expected_y = [370.05, 92.89, 23.60, 3.98, 1.24, 0.56]

# plt.figure()
# plt.plot(sim_mem_eff_sorted, sim_times_sorted, marker='o', label='Simulated')
# plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# plt.legend()
# plt.xlabel("Memory Efficiency")
# plt.ylabel("Simulation Time per Ent Pair (s)")
# plt.title("Average Simulation Time to Generate Entanglement")
# plt.grid(True)
# plt.savefig('sim_time_to_mem_eff.png')

# print(sim_mem_eff_sorted)
# print(sim_times_sorted)

# print(sim_expected_x)
# print(sim_expected_y)