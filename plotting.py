import matplotlib.pyplot as plt
import re
import glob

log_files = glob.glob("dark_count=*.log")

# trap_freqs_25 = []
# times_to_ent_25 = []
# trap_freqs_50 = []
# times_to_ent_50 = []


# for filename in log_files:
#     mem25_match = re.search(r"mem_eff=0.25", filename)
#     if mem25_match:
#         retrap = None
#         ent_time = None
#         retrap_match = re.search(r"retrap=([\d.]+)", filename)
#         if retrap_match:
#             retrap = retrap_match.group(1)
#         with open(filename, 'r') as f:
#             for line in f:
#                 ent_time_match = re.search(r"At end, avg time to ent was (\d+\.\d+)", line)
#                 if ent_time_match:
#                     ent_time = float(ent_time_match.group(1))
#                     break
#         trap_freqs_25.append(int(retrap))
#         times_to_ent_25.append(ent_time)
#     # mem50_match = re.search(r"mem_eff=0.5", filename)
#     # if mem50_match:
#     #     retrap = None
#     #     ent_time = None
#     #     retrap_match = re.search(r"retrap=([\d.]+)", filename)
#     #     if retrap_match:
#     #         retrap = retrap_match.group(1)
#     #     with open(filename, 'r') as f:
#     #         for line in f:
#     #             ent_time_match = re.search(r"At end, avg time to ent was (\d+\.\d+)", line)
#     #             if ent_time_match:
#     #                 ent_time = float(ent_time_match.group(1))
#     #                 break
#     #     trap_freqs_50.append(int(retrap))
#     #     times_to_ent_50.append(ent_time)
    

# sorted_pairs = sorted(zip(trap_freqs_25, times_to_ent_25))
# x_sorted, y_sorted = zip(*sorted_pairs)

# freqs_sorted = list(x_sorted)
# times_sorted = list(y_sorted)

# print(freqs_sorted)
# print(times_sorted)

# plt.figure()
# plt.plot(freqs_sorted, times_sorted, marker='o')
# plt.xlabel("Attempts Per Atom Load")
# plt.ylabel("Simulation Time per Ent Pair (s)")
# plt.title("Entanglement Time for Mem_Eff=0.25")
# plt.grid(True)
# plt.savefig('ent_time_from_retrap_times.png')
# plt.show()


# old plots
# compute_mem_eff = []
# compute_times = []

# sim_mem_eff = []
# sim_times = []

# fid_mem_eff = []
# fids = []

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
#             fid_match = re.search(r"Total Fidelity was: (\d+\.\d+).", line)
#             if fid_match:
#                 fid_mem_eff.append(mem_eff)
#                 fids.append(float(fid_match.group(1)))
            



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

# # sim_expected_x = ['0.025', '0.05', '0.1', '0.25', '0.5', '1.0']
# # sim_expected_y = [370.05, 92.89, 23.60, 3.98, 1.24, 0.56]

# plt.figure()
# plt.plot(sim_mem_eff_sorted, sim_times_sorted, marker='o', label='Simulated')
# # plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# # plt.legend()
# plt.xlabel("Memory Efficiency")
# plt.ylabel("Simulation Time per Ent Pair (s)")
# plt.title("Average Simulation Time to Generate Entanglement")
# plt.grid(True)
# plt.savefig('sim_time_to_mem_eff.png')

# print(sim_mem_eff_sorted)
# print(sim_times_sorted)

# # print(sim_expected_x)
# # print(sim_expected_y)

# fid_sorted_pairs = sorted(zip(fid_mem_eff, fids))
# fid_x_sorted, fid_y_sorted = zip(*fid_sorted_pairs)

# fid_mem_eff_sorted = list(fid_x_sorted)
# fid_sorted = list(fid_y_sorted)


# plt.figure()
# plt.plot(fid_mem_eff_sorted, fid_sorted, marker='o', label='Simulated')
# # plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# # plt.legend()
# plt.xlabel("Memory Efficiency")
# plt.ylabel("Entanglement Fidelity")
# plt.title("Fidelity vs Memory Efficiency")
# plt.grid(True)
# plt.savefig('fidelity_to_mem_eff.png')

# print(sim_mem_eff_sorted)
# print(sim_times_sorted)



dark_counts = []
fids = []

for filename in log_files:
    dark_count = None
    dc_match = re.search(r"dark_count=([\d.]+)", filename)
    if dc_match:
        dark_count = dc_match.group(1)
    with open(filename, 'r') as f:
        for line in f:
            fid_match = re.search(r"Total Fidelity was: (\d+\.\d+).", line)
            if fid_match:
                dark_counts.append(dark_count)
                fids.append(float(fid_match.group(1)))


sorted_pairs = sorted(zip(dark_counts, fids))
x_sorted, y_sorted = zip(*sorted_pairs)


dc_sorted = list(x_sorted)
fid_sorted = list(y_sorted)


plt.figure()
plt.plot(dc_sorted, fid_sorted, marker='o', label='Simulated')
# plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# plt.legend()
plt.xlabel("Dark Count Rate (Hz)")
plt.ylabel("Entanglement Fidelity")
plt.title("Fidelity vs Dark Count Rate (Mem Eff = 0.25)")
plt.grid(True)
plt.savefig('fidelity_to_dark_count.png')

print(dc_sorted)
print(fid_sorted)