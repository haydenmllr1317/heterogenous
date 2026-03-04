import matplotlib.pyplot as plt
import re
import glob
import numpy as np



## BIG FIGURE
plt.rcParams["font.size"] = 14
fig, axes = plt.subplots(1, 2,figsize=(9,3.4))
fig.subplots_adjust(left=0.07, right=0.99, top=0.95, bottom=0.24, wspace=0.27)

# log_files = [glob.glob('tmp/data/qfc_eff/qfc_eff=*.log'), glob.glob('tmp/data/qfc_noise/qfc_noise=*.log'), glob.glob('tmp/data/uw_eff/uw_eff=*.log'), glob.glob('tmp/data/uw_noise/uw_noise=*.log'), glob.glob('tmp/data/coherence/coherence=*.log')]
log_files = [glob.glob('tmp/data/ideal_coherence/coherence=*.log'), glob.glob('tmp/data/realistic_coherence/coherence=*.log')] # , glob.glob('tmp/data/qfc_noise/qfc_noise=*.log'), glob.glob('tmp/data/uw_noise/uw_noise=*.log')]

colors = ['blue', 'red']
labels = ['Optimistic', 'Default']
markers = ['s', '^']

for i in range(len(log_files)):
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
    vars_sorted = [z*1e-9 for z in vars_sorted]
    vars_even = np.arange(len(vars_sorted))

    fids_sorted = list(y1_sorted)

    sorted_pairs = sorted(zip(variables, rates))
    x_sorted, y2_sorted = zip(*sorted_pairs)

    rates_sorted = list(y2_sorted)

    axes[1].plot(vars_even[1:], fids_sorted[1:], color=colors[i], label=labels[i], marker=markers[i], markersize=6)
    axes[0].plot(vars_even[1:], rates_sorted[1:], color=colors[i], label=labels[i], marker=markers[i], markersize=6)


axes[1].set_xticks(vars_even[1:])
axes[1].set_xticklabels(vars_sorted[1:])
axes[1].tick_params(axis='x')
axes[1].set_xlabel("Transmon T1 Coherence Time (ms)\n(b)")

axes[0].set_xticks(vars_even[1:])
axes[0].set_xticklabels(vars_sorted[1:])
axes[0].tick_params(axis='x')
axes[0].set_xlabel("Transmon T1 Coherence Time (ms)\n(a)")


# axes[0].set_xlabel('QFC Efficiency\n(a)')
axes[1].set_ylabel("Fidelity")
axes[1].set_ylim(-0.2,0.8)
# axes[0].set_xscale('log')
axes[1].legend()
axes[1].grid(True)
axes[0].set_ylabel("Rate (Hz)")
axes[0].set_ylim(0,12)
axes[0].grid(True)
# axes[1].set_xscale('log')
axes[0].legend(loc='upper left')

# plt.rcParams["font.size"] = 20

plt.savefig('tmp/trial3.png')

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