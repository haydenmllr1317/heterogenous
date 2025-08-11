import matplotlib.pyplot as plt
import re
import glob

# log_files = glob.glob("dark_count=*.log")
log_files_1389 = glob.glob("pce=*,lambda=1389,*.log")
log_files_556 = glob.glob("pce=*,lambda=556,*.log")

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
sim_mem_eff1389 = []
sim_times1389 = []

fid_mem_eff1389 = []
fids1389 = []

attempts_mem_eff1389 = []
ent_attempts1389 = []

for filename in log_files_1389:
    mem_eff = None
    num_trials = None
    mem_match = re.search(r"pce=([\d.]+)", filename)
    if mem_match:
        mem_eff = mem_match.group(1)
    n_match = re.search(r"num_trials=(\d+)", filename)
    if n_match:
        num_trials = int(n_match.group(1))
    with open(filename, 'r') as f:
        for line in f:
            # compute_match = re.search(r"At end, computer took (\d+\.\d+) seconds.", line)
            # if compute_match:
            #     compute_mem_eff.append(mem_eff)
            #     compute_times.append(float(compute_match.group(1))/num_trials)
            sim_match = re.search(r"Average ent time is (\d+\.\d+)", line)
            if sim_match:
                sim_mem_eff1389.append(mem_eff)
                sim_times1389.append(float(sim_match.group(1)))
            fid_match = re.search(r"calculated fidelity is (\d+\.\d+).", line)
            if fid_match:
                fid_mem_eff1389.append(mem_eff)
                fids1389.append(float(fid_match.group(1)))
            attempts_match = re.search(r"were generated after (\d+) attempts.", line)
            if attempts_match:
                attempts_mem_eff1389.append(mem_eff)
                ent_attempts1389.append(float(attempts_match.group(1))/num_trials)

sim_mem_eff556 = []
sim_times556 = []

fid_mem_eff556 = []
fids556 = []

attempts_mem_eff556 = []
ent_attempts556 = []

for filename in log_files_556:
    mem_eff = None
    num_trials = None
    mem_match = re.search(r"pce=([\d.]+)", filename)
    if mem_match:
        mem_eff = mem_match.group(1)
    n_match = re.search(r"num_trials=(\d+)", filename)
    if n_match:
        num_trials = int(n_match.group(1))
    with open(filename, 'r') as f:
        for line in f:
            # compute_match = re.search(r"At end, computer took (\d+\.\d+) seconds.", line)
            # if compute_match:
            #     compute_mem_eff.append(mem_eff)
            #     compute_times.append(float(compute_match.group(1))/num_trials)
            sim_match = re.search(r"Average ent time is (\d+\.\d+)", line)
            if sim_match:
                sim_mem_eff556.append(mem_eff)
                sim_times556.append(float(sim_match.group(1)))
            fid_match = re.search(r"calculated fidelity is (\d+\.\d+).", line)
            if fid_match:
                fid_mem_eff556.append(mem_eff)
                fids556.append(float(fid_match.group(1)))
            attempts_match = re.search(r"were generated after (\d+) attempts.", line)
            if attempts_match:
                attempts_mem_eff556.append(mem_eff)
                ent_attempts556.append(float(attempts_match.group(1))/num_trials)
            



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

sim_sorted_pairs1389 = sorted(zip(sim_mem_eff1389, sim_times1389))
sim_x_sorted1389, sim_y_sorted1389 = zip(*sim_sorted_pairs1389)

sim_mem_eff_sorted1389 = list(sim_x_sorted1389)
sim_times_sorted1389 = list(sim_y_sorted1389)

sim_sorted_pairs556 = sorted(zip(sim_mem_eff556, sim_times556))
sim_x_sorted556, sim_y_sorted556 = zip(*sim_sorted_pairs556)

sim_mem_eff_sorted556 = list(sim_x_sorted556)
sim_times_sorted556 = list(sim_y_sorted556)

# sim_expected_x = ['0.025', '0.05', '0.1', '0.25', '0.5', '1.0']
# sim_expected_y = [370.05, 92.89, 23.60, 3.98, 1.24, 0.56]

plt.figure()
plt.plot(sim_mem_eff_sorted1389, sim_times_sorted1389, marker='o', label='1389')
plt.plot(sim_mem_eff_sorted556, sim_times_sorted556, marker='o', label='556')
# plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
plt.legend()
plt.yscale('log')
plt.xlabel("Photon Collection Efficiency")
plt.ylabel("Simulation Time per Ent Pair (s)")
plt.title("Average Simulation Time to Generate Entanglement")
plt.grid(True)
plt.savefig('sim_time_to_pce.png')

# print(sim_mem_eff_sorted)
# print(sim_times_sorted)

# print(sim_expected_x)
# print(sim_expected_y)

fid_sorted_pairs1389 = sorted(zip(fid_mem_eff1389, fids1389))
fid_x_sorted1389, fid_y_sorted1389 = zip(*fid_sorted_pairs1389)

fid_mem_eff_sorted1389 = list(fid_x_sorted1389)
fid_sorted1389 = list(fid_y_sorted1389)

fid_sorted_pairs556 = sorted(zip(fid_mem_eff556, fids556))
fid_x_sorted556, fid_y_sorted556 = zip(*fid_sorted_pairs556)

fid_mem_eff_sorted556= list(fid_x_sorted556)
fid_sorted556 = list(fid_y_sorted556)


plt.figure()
plt.plot(fid_mem_eff_sorted1389, fid_sorted1389, marker='o', label='1389')
plt.plot(fid_mem_eff_sorted556, fid_sorted556, marker='o', label='556')
# plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
plt.legend()
plt.xlabel("Photon Collection Efficiency")
plt.ylabel("Entanglement Fidelity")
plt.title("Fidelity vs Photon Collection Efficiency")
plt.grid(True)
plt.savefig('fidelity_to_pce.png')

# print(sim_mem_eff_sorted)
# print(sim_times_sorted)


attempts_sorted_pairs1389 = sorted(zip(attempts_mem_eff1389, ent_attempts1389))
attempts_x_sorted1389, attempts_y_sorted1389 = zip(*attempts_sorted_pairs1389)

attempts_mem_eff_sorted1389 = list(attempts_x_sorted1389)
ent_attempts_sorted1389 = list(attempts_y_sorted1389)

attempts_sorted_pairs556 = sorted(zip(attempts_mem_eff556, ent_attempts556))
attempts_x_sorted556, attempts_y_sorted556 = zip(*attempts_sorted_pairs556)

attempts_mem_eff_sorted556 = list(attempts_x_sorted556)
ent_attempts_sorted556 = list(attempts_y_sorted556)


plt.figure()
plt.plot(attempts_mem_eff_sorted1389, ent_attempts_sorted1389, marker='o', label='1389')
plt.plot(attempts_mem_eff_sorted556, ent_attempts_sorted556, marker='o', label='556')
# plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
plt.legend()
plt.yscale('log')
plt.xlabel("Photon Collection Efficiency")
plt.ylabel("Entanglement Attempts per Success")
plt.title("Entanglement Attempts per Success vs Photon Collection Efficiency")
plt.grid(True)
plt.savefig('ent_attempts_to_pce.png')

# print(sim_mem_eff_sorted)
# print(sim_times_sorted)



# dark_counts = []
# fids = []

# for filename in log_files:
#     dark_count = None
#     dc_match = re.search(r"dark_count=([\d.]+)", filename)
#     if dc_match:
#         dark_count = dc_match.group(1)
#     with open(filename, 'r') as f:
#         for line in f:
#             fid_match = re.search(r"Total Fidelity was: (\d+\.\d+).", line)
#             if fid_match:
#                 dark_counts.append(dark_count)
#                 fids.append(float(fid_match.group(1)))


# sorted_pairs = sorted(zip(dark_counts, fids))
# x_sorted, y_sorted = zip(*sorted_pairs)


# dc_sorted = list(x_sorted)
# fid_sorted = list(y_sorted)


# plt.figure()
# plt.plot(dc_sorted, fid_sorted, marker='o', label='Simulated')
# # plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# # plt.legend()
# plt.xlabel("Dark Count Rate (Hz)")
# plt.ylabel("Entanglement Fidelity")
# plt.title("Fidelity vs Dark Count Rate (Mem Eff = 0.25)")
# plt.grid(True)
# plt.savefig('fidelity_to_dark_count.png')

# print(dc_sorted)
# print(fid_sorted)