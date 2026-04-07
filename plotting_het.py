import matplotlib.pyplot as plt
import re
import glob


# logs = glob.glob('tmp/data/coherence/coherence=*.log')

# fids = []
# rates = []
# variables = []


# for filename in logs:
#     with open(filename, 'r') as f:
#         for line in f:
#             var_index = line.find(':')
#             if var_index != -1:
#                 variables.append(float(line[var_index+1:-1]))

#             fid_index = line.find('=')
#             if fid_index != -1:
#                 fids.append(float(line[fid_index+1:-1]))
            
#             rates_index = line.find('~')
#             if rates_index != -1:
#                 rates.append(1/(float(line[rates_index+1:-1])))
                
# print(len(variables))
# print(len(fids))
# print(len(rates))

# sorted_pairs = sorted(zip(variables, fids))
# x_sorted, y1_sorted = zip(*sorted_pairs)

# vars_sorted = list(x_sorted)
# fids_sorted = list(y1_sorted)

# sorted_pairs = sorted(zip(variables, rates))
# x_sorted, y2_sorted = zip(*sorted_pairs)

# rates_sorted = list(y2_sorted)

# fig, ax1 = plt.subplots()

# ax1.plot(vars_sorted, fids_sorted, color='blue')
# ax1.set_ylabel("Fidelity", color='blue')
# ax1.tick_params(axis='y', colors='blue')
# ax1.set_ylim(0.3,0.7) # for qfc efficiency
# # ax1.set_ylim(0,1)



# # Right y-axis
# ax2 = ax1.twinx()
# ax2.plot(vars_sorted, rates_sorted, color='red')
# ax2.set_ylabel("Rate (Hz)", color='red')
# ax2.tick_params(axis='y', colors='red')
# ax2.set_ylim(2,4)

# # plt.figure()d
# # plt.plot(rates_sorted, fids_sorted, marker='o')
# # plt.xlim(0,0.501)
# # plt.xticks(rates_sorted[::5])
# # # plt.plot(sim_mem_eff_sorted556, sim_times_sorted556, marker='o', label='556')
# # # plt.plot(sim_expected_x, sim_expected_y, marker='o', label='Expected')
# # # plt.legend()
# # # plt.yscale('log')
# # plt.xlabel("QFC Noise Rate")
# # plt.ylabel("Fidelity")
# # plt.ylim(0,1)
# # plt.title("Yb-Yb Entanglement Fidelity vs QFC Noise")
# plt.grid(True)
# plt.savefig('tmp/coherence.png')



## BIG FIGURE

fig, axes = plt.subplots(1, 3,figsize=(13,3))
fig.subplots_adjust(left=0.06, right=0.95, top=0.95, bottom=0.21, wspace=0.4)
ax2 = [None] * len(axes)

# log_files = [glob.glob('tmp/data/qfc_eff/qfc_eff=*.log'), glob.glob('tmp/data/qfc_noise/qfc_noise=*.log'), glob.glob('tmp/data/uw_eff/uw_eff=*.log'), glob.glob('tmp/data/uw_noise/uw_noise=*.log'), glob.glob('tmp/data/coherence/coherence=*.log')]
log_files = [glob.glob('tmp/data/qfc_eff/qfc_eff=*.log'), glob.glob('tmp/data/qfc_noise/qfc_noise=*.log'), glob.glob('tmp/data/uw_noise/uw_noise=*.log')]


for i in range(len(axes)):
    fids = []
    rates = []
    variables = []

    for filename in log_files[i]:
        with open(filename, 'r') as f:
            for line in f:
                var_index = line.find(':')
                if var_index != -1:
                    variables.append(float(line[var_index+1:-1]))

                fid_index = line.find('=')
                if fid_index != -1:
                    fids.append(float(line[fid_index+1:-1]))
                
                rates_index = line.find('~')
                if rates_index != -1:
                    rates.append(1/(float(line[rates_index+1:-1])))
                    
    print(len(variables))
    print(len(fids))
    print(len(rates))

    sorted_pairs = sorted(zip(variables, fids))
    x_sorted, y1_sorted = zip(*sorted_pairs)

    vars_sorted = list(x_sorted)
    if i == 3:
        vars_sorted = [z*1e-6 for z in vars_sorted]
    fids_sorted = list(y1_sorted)

    sorted_pairs = sorted(zip(variables, rates))
    x_sorted, y2_sorted = zip(*sorted_pairs)

    rates_sorted = list(y2_sorted)

    axes[i].plot(vars_sorted, fids_sorted, color='blue')
    axes[i].set_ylabel("Fidelity", color='blue')
    axes[i].set_ylim(0.2,0.8)
    axes[i].tick_params(axis='y', colors='blue')
    axes[i].grid(True)
    # plt.xlim(0,251)
    # plt.xticks(reload_sorted[::5])

    ax2[i] = axes[i].twinx()
    ax2[i].plot(vars_sorted, rates_sorted, color='red')
    ax2[i].set_ylabel("Rate (Hz)", color='red')
    ax2[i].set_ylim(0,5.0)
    ax2[i].tick_params(axis='y', colors='red')


axes[0].set_xlabel('QFC Efficiency\n(a)')
axes[1].set_xlabel('QFC Noise\n(b)')
# axes[2].set_xlabel('Transducer Efficiency\n(c)')
axes[2].set_xlabel('Transducer Noise\n(c)')

plt.savefig('tmp/mixed.png')

'''

######################################### ORGANIZED PLOTS #########################################
#
################################## RELOAD_COUNT PLOTS #############################################


fig, axes = plt.subplots(1, 3,figsize=(13,3.5))
fig.subplots_adjust(left=0.06, right=0.95, top=0.95, bottom=0.18, wspace=0.45)

log_files_reload = glob.glob('tmp/data/reload/reload=*.log')

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
axes[1].plot(reload_sorted, fids_sorted, color='blue')
axes[1].set_ylabel("Fidelity", color='blue')
axes[1].set_ylim(0.8,1)
axes[1].tick_params(axis='y', colors='blue')
axes[1].grid(True)
# plt.xlim(0,251)
# plt.xticks(reload_sorted[::5])

ax12 = axes[1].twinx()
ax12.plot(reload_sorted, rates_sorted, color='red')
ax12.set_ylabel("Rate (Hz)", color='red')
ax12.set_ylim(0,1.0)
ax12.tick_params(axis='y', colors='red')

axes[1].set_xlabel('Reload Number\n(b)')

# plt.xlabel("Reload Number")
# # plt.ylabel("Fidelity")
# # plt.ylim(0,1)
# plt.title("Yb-Yb Entanglement vs Reload Count")
# plt.grid(True)
# plt.savefig('tmp/reloads.png')

###################################################################################################
#
################################## BIN WIDTH PLOTS #############################################


log_files_width = glob.glob('tmp/data/binwidth/width=*.log')

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
reload_sorted = [z*1e-6 for z in reload_sorted]
rates_sorted = list(y2_sorted)

# fig, ax1 = plt.subplots()
axes[2].plot(reload_sorted, fids_sorted, color='blue')
axes[2].set_ylabel("Fidelity", color='blue')
axes[2].set_ylim(0.8,1)
axes[2].tick_params(axis='y', colors='blue')
axes[2].grid(True)
# plt.xlim(0,251)
# plt.xticks(reload_sorted[::5])

ax22 = axes[2].twinx()
ax22.plot(reload_sorted, rates_sorted, color='red')
ax22.set_ylabel("Rate (Hz)", color='red')
ax22.set_ylim(0,1.0)
ax22.tick_params(axis='y', colors='red')

axes[2].set_xlabel('Time Bin Width (microseconds)\n(c)')
# plt.xlabel("Bin Width")
# plt.ylabel("Fidelity")
# plt.ylim(0,1)
# plt.title("Yb-Yb Link")
# plt.grid(True)


###################################################################################################
#
################################## BIN WIDTH PLOTS #############################################


log_files_pce = glob.glob('tmp/data/pce/pce=*.log')

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
axes[0].plot(pces_sorted, fids_sorted, color='blue')
axes[0].set_ylabel("Fidelity", color='blue')
axes[0].set_ylim(0.8,1)
axes[0].tick_params(axis='y', colors='blue')
axes[0].grid(True)
# plt.xlim(0,251)
# plt.xticks(reload_sorted[::5])

ax02 = axes[0].twinx()
ax02.plot(pces_sorted, rates_sorted, color='red')
ax02.set_ylabel("Rate (Hz)", color='red')
ax02.set_ylim(0,1)
ax02.tick_params(axis='y', colors='red')

axes[0].set_xlabel('Photon Collection Efficiency\n(a)')
# plt.xlabel("Bin Width")
# plt.ylabel("Fidelity")
# plt.ylim(0,1)
# plt.title("Yb-Yb Link")
# plt.grid(True)


###################################################################################################
#
###################################################################################################


# plt.tight_layout()
plt.savefig('tmp/all_new.png')

'''