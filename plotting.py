import matplotlib.pyplot as plt
import re
import glob
<<<<<<< HEAD

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
=======
import numpy as np

######################################### ORGANIZED PLOTS #########################################
#
#
#################################### FIDELITY(QFC_NOISE) PLOTS ####################################

# log_files_fid_vs_qfc_noise = glob.glob('tmp/data/fid(qfc_noise)/qfc_noise=*.log')

# fids = []
# qfc_noise = []

# i = 0

# for filename in log_files_fid_vs_qfc_noise:
#     i += 1
#     # print(i)

#     with open(filename, 'r') as f:
#         for line in f:
#             noise_index = line.find(':')
#             if noise_index != -1:
#                 qfc_noise.append(float(line[noise_index+1:-1]))

#             fid_index = line.find('=')
#             if fid_index != -1:
#                 fids.append(float(line[fid_index+1:-1]))
                

# print(len(qfc_noise))
# print(len(fids))

# fids_vs_qfc_sorted_pairs = sorted(zip(qfc_noise, fids))
# x_sorted, y_sorted = zip(*fids_vs_qfc_sorted_pairs)

# noise_sorted = list(x_sorted)#[:20]
# fids_sorted = list(y_sorted)#[:20]

# print(noise_sorted)

# plt.figure()
# plt.plot(noise_sorted, fids_sorted, marker='o')
# plt.xlim(0,0.501)
# plt.xticks(noise_sorted[::5])
# # plt.plot(sim_mem_eff_sorted556, sim_times_sorted556, marker='o', label='556')
# # plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# # plt.legend()
# # plt.yscale('log')
# plt.xlabel("QFC Noise Rate")
# plt.ylabel("Fidelity")
# plt.ylim(0,1)
# plt.title("Yb-Yb Entanglement Fidelity vs QFC Noise")
# plt.grid(True)
# plt.savefig('tmp/fid_to_QFC_noise_newest.png')

###################################################################################################
#
################################## RELOAD_COUNT PLOTS #############################################


fig, axes = plt.subplots(1, 3,figsize=(13,3))
fig.subplots_adjust(left=0.06, right=0.95, top=0.95, bottom=0.21, wspace=0.4)

log_files_reload = glob.glob('tmp/data/qfc_noise/qfc_noise=*.log')

fids = []
rates = []
reload = []

i = 0

for filename in log_files_reload:
    i += 1
    # print(i)
    with open(filename, 'r') as f:
        for line in f:
            reload_index = line.find(':')
            if reload_index != -1:
                reload.append(float(line[reload_index+1:-1]))

            fid_index = line.find('=')
            if fid_index != -1:
                fids.append(float(line[fid_index+1:-1]))
            
            rates_index = line.find('~')
            if rates_index != -1:
                rates.append(1/(float(line[rates_index+1:-1])))
                
print(len(reload))
print(len(fids))
print(len(rates))

fids_vs_reload_sorted_pairs = sorted(zip(reload, fids))
x_sorted, y1_sorted = zip(*fids_vs_reload_sorted_pairs)

reload_sorted = list(x_sorted)
fids_sorted = list(y1_sorted)

rates_vs_reload_sorted_pairs = sorted(zip(reload, rates))
x_sorted, y2_sorted = zip(*rates_vs_reload_sorted_pairs)

rates_sorted = list(y2_sorted)

# fig, ax1 = plt.subplots()
axes[1].plot(reload_sorted, fids_sorted, color='blue', marker='s', markersize=4)
axes[1].set_ylabel("Fidelity", color='blue')
axes[1].set_ylim(0.2,0.8)
axes[1].tick_params(axis='y', colors='blue')
axes[1].grid(True)
# plt.xlim(0,251)
# plt.xticks(reload_sorted[::5])

ax12 = axes[1].twinx()
ax12.plot(reload_sorted, rates_sorted, color='red', marker='^', markersize=4)
ax12.set_ylabel("Rate (Hz)", color='red')
ax12.set_ylim(0,5)
ax12.tick_params(axis='y', colors='red')

axes[1].set_xlabel('QFC Noise\n(b)')

# plt.xlabel("Reload Number")
# # plt.ylabel("Fidelity")
# # plt.ylim(0,1)
# plt.title("Yb-Yb Entanglement vs Reload Count")
# plt.grid(True)
# plt.savefig('tmp/reloads.png')

###################################################################################################
#
################################## BIN WIDTH PLOTS #############################################


log_files_width = glob.glob('tmp/data/uw_noise/uw_noise=*.log')

fids = []
rates = []
width = []

i = 0

for filename in log_files_width:
    i += 1
    # print(i)
    with open(filename, 'r') as f:
        for line in f:
            width_index = line.find(':')
            if width_index != -1:
                width.append(float(line[width_index+1:-1]))

            fid_index = line.find('=')
            if fid_index != -1:
                fids.append(float(line[fid_index+1:-1]))
            
            rates_index = line.find('~')
            if rates_index != -1:
                rates.append(1/(float(line[rates_index+1:-1])))
                
print(len(width))
print(len(fids))
print(len(rates))

fids_vs_reload_sorted_pairs = sorted(zip(width, fids))
x_sorted, y1_sorted = zip(*fids_vs_reload_sorted_pairs)


fids_sorted = list(y1_sorted)

rates_vs_reload_sorted_pairs = sorted(zip(width, rates))
x_sorted, y2_sorted = zip(*rates_vs_reload_sorted_pairs)

reload_sorted = list(x_sorted)
# reload_sorted = [z*1e-6 for z in reload_sorted]
rates_sorted = list(y2_sorted)

# fig, ax1 = plt.subplots()
axes[2].plot(reload_sorted, fids_sorted, color='blue', marker='s', markersize=4)
axes[2].set_ylabel("Fidelity", color='blue')
axes[2].set_ylim(0.2,0.8)
axes[2].tick_params(axis='y', colors='blue')
axes[2].grid(True)
# plt.xlim(0,251)
# plt.xticks(reload_sorted[::5])

ax22 = axes[2].twinx()
ax22.plot(reload_sorted, rates_sorted, color='red', marker='^', markersize=4)
ax22.set_ylabel("Rate (Hz)", color='red')
ax22.set_ylim(0,5)
ax22.tick_params(axis='y', colors='red')

axes[2].set_xlabel('Transducer Noise\n(c)')
# plt.xlabel("Bin Width")
# plt.ylabel("Fidelity")
# plt.ylim(0,1)
# plt.title("Yb-Yb Link")
# plt.grid(True)


###################################################################################################
#
################################## BIN WIDTH PLOTS #############################################


log_files_pce = glob.glob('tmp/data/qfc_eff/qfc_eff=*.log')

fids = []
rates = []
pces = []

i = 0

for filename in log_files_pce:
    i += 1
    # print(i)
    with open(filename, 'r') as f:
        for line in f:
            pce_index = line.find(':')
            if pce_index != -1:
                pces.append(round(float(line[pce_index+1:-1]),2))

            fid_index = line.find('=')
            if fid_index != -1:
                fids.append(float(line[fid_index+1:-1]))
            
            rates_index = line.find('~')
            if rates_index != -1:
                rates.append(1/(float(line[rates_index+1:-1])))
                
print(len(pces))
print(len(fids))
print(len(rates))

fids_vs_pce_sorted_pairs = sorted(zip(pces, fids))
x_sorted, y1_sorted = zip(*fids_vs_pce_sorted_pairs)

pces_sorted = list(x_sorted)
fids_sorted = list(y1_sorted)

rates_vs_pce_sorted_pairs = sorted(zip(pces, rates))
x_sorted, y2_sorted = zip(*rates_vs_pce_sorted_pairs)

rates_sorted = list(y2_sorted)

# fig, ax1 = plt.subplots()
axes[0].plot(pces_sorted, fids_sorted, color='blue', marker='s', markersize=4)
axes[0].set_ylabel("Fidelity", color='blue')
axes[0].set_ylim(0.2,0.8)
axes[0].tick_params(axis='y', colors='blue')
axes[0].grid(True)
axes[0].set_xticks(np.arange(0.2, 1.2, 0.2)) 
# plt.xlim(0,251)
# plt.xticks(reload_sorted[::5])

ax02 = axes[0].twinx()
ax02.plot(pces_sorted, rates_sorted, color='red', marker='^', markersize=4)
ax02.set_ylabel("Rate (Hz)", color='red')
ax02.set_ylim(0,5)
ax02.tick_params(axis='y', colors='red')

axes[0].set_xlabel('QFC Efficiency\n(a)')



# plt.xlabel("Bin Width")
# plt.ylabel("Fidelity")
# plt.ylim(0,1)
# plt.title("Yb-Yb Link")
# plt.grid(True)


###################################################################################################
#
###################################################################################################


# plt.tight_layout()
plt.savefig('tmp/trial2.png')
>>>>>>> 1e886777b0e9f9344b951237a07276ab6e4460ec
