import time
from subprocess import Popen, PIPE

def get_output(p: Popen):
    stderr = p.stderr.readlines()
    if stderr:
        for line in stderr:
            print(line)

# wavelengths = [556, 1389]
# parameters = {1.0: 200, 0.5: 200, 0.25: 200}#, 0.1: 200, 0.05: 200, 0.025: 200}
# tasks = []

# command = ['python3', 'main_yb_yb_EG_sim.py']

# for wl in wavelengths:
#     for key in parameters.keys():
#         args = []
#         args.append('-eff')
#         args.append(str(key))
#         args.append('-n')
#         args.append(str(parameters[key]))
#         args.append('-wavelength')
#         args.append(str(wl))
#         tasks.append(command+args)

# parallel = 10
# ps = []
# while len(tasks) > 0 or len(ps) > 0:
#     if len(ps) < parallel and len(tasks) > 0:
#         task = tasks.pop(0)
#         print(task, f'{len(tasks)} still in queue')
#         ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
#     else:
#         time.sleep(0.05)
#         new_ps = []
#         for p in ps:
#             if p.poll() is None:
#                 new_ps.append(p)
#             else:
#                 get_output(p)
#         ps = new_ps

# numlist = [10, 100, 1000, 10000, 100000]
# # alternative runner for retrap
# for element in numlist:
#     args = []
#     args.append('-eff')
#     args.append(str(0.25))
#     args.append('-n')
#     args.append(str(100))
#     # args.append('-retrap')
#     # args.append(str(i+5))
#     args.append('-darkc')
#     args.append(str(element))
#     tasks.append(command+args)

# parallel = 10
# ps = []
# while len(tasks) > 0 or len(ps) > 0:
#     if len(ps) < parallel and len(tasks) > 0:
#         task = tasks.pop(0)
#         print(task, f'{len(tasks)} still in queue')
#         ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
#     else:
#         time.sleep(0.05)
#         new_ps = []
#         for p in ps:
#             if p.poll() is None:
#                 new_ps.append(p)
#             else:
#                 get_output(p)
#         ps = new_ps

'''
# NOTE VARYING: QFC DARK COUNT
tasks = []

command = ['python3', 'main_yb_yb_EG_sim.py']

for i in range(51):
    args = []
    args.append('-qfc_noise')
    x = 0.01*(i)
    args.append(str(x))
    tasks.append(command+args)

parallel = 10
ps = []
while len(tasks) > 0 or len(ps) > 0:
    if len(ps) < parallel and len(tasks) > 0:
        task = tasks.pop(0)
        print(task, f'{len(tasks)} still in queue')
        ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
    else:
        time.sleep(0.05)
        new_ps = []
        for p in ps:
            if p.poll() is None:
                new_ps.append(p)
            else:
                get_output(p)
        ps = new_ps
'''
        
'''
# NOTE VARYING: RETRAP NUM
tasks = []

command = ['python3', 'main_yb_yb_EG_sim.py']

for i in range(49):
    args = []
    args.append('-reloadcount')
    x = 5*(i) + 10
    args.append(str(x))
    tasks.append(command+args)

parallel = 10
ps = []
while len(tasks) > 0 or len(ps) > 0:
    if len(ps) < parallel and len(tasks) > 0:
        task = tasks.pop(0)
        print(task, f'{len(tasks)} still in queue')
        ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
    else:
        time.sleep(0.05)
        new_ps = []
        for p in ps:
            if p.poll() is None:
                new_ps.append(p)
            else:
                get_output(p)
        ps = new_ps
'''


# # NOTE VARYING: BIN WIDTH
# tasks = []

# command = ['python3', 'main_yb_yb_EG_sim.py']

# for i in range(49):
#     args = []
#     args.append('-bwidth')
#     x = 500_000 + 20_000*(i)
#     args.append(str(x))
#     tasks.append(command+args)

# parallel = 10
# ps = []
# while len(tasks) > 0 or len(ps) > 0:
#     if len(ps) < parallel and len(tasks) > 0:
#         task = tasks.pop(0)
#         print(task, f'{len(tasks)} still in queue')
#         ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
#     else:
#         time.sleep(0.05)
#         new_ps = []
#         for p in ps:
#             if p.poll() is None:
#                 new_ps.append(p)
#             else:
#                 get_output(p)
#         ps = new_ps

# NOTE VARYING: detector dark counts
tasks = []

command = ['python3', 'main_yb_yb_EG_sim.py']

for i in range(50):
    args = []
    args.append('-dtctor_dc')
    x = 10 + 2000*(i)
    args.append(str(x))
    tasks.append(command+args)

parallel = 1
ps = []
while len(tasks) > 0 or len(ps) > 0:
    if len(ps) < parallel and len(tasks) > 0:
        task = tasks.pop(0)
        print(task, f'{len(tasks)} still in queue')
        ps.append(Popen(task, stdout=PIPE, stderr=PIPE))
    else:
        time.sleep(0.05)
        new_ps = []
        for p in ps:
            if p.poll() is None:
                new_ps.append(p)
            else:
                get_output(p)
        ps = new_ps






# TODO generate plots with these figures:
# Yb-Yb entanglement fidelity as function of QFC dark count rate
# Yb-Yb entanglement fidelity as function of QFC efficiency
# Yb-Yb 1389 vs 556 entanglement generation time

# less necessary
# 556 ideal reload time (ent time as function of reload time)

# skip for now
# Transmon-Transom and/or Transmon-Yb 