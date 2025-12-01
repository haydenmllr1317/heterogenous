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
        

# # NOTE VARYING: RETRAP NUM
# tasks = []

# command = ['python3', 'main_yb_yb_EG_sim.py']

# for i in range(50):
#     args = []
#     args.append('-reloadcount')
#     x = 5*(i+1)
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



# # NOTE VARYING: BIN WIDTH
# tasks = []

# command = ['python3', 'main_yb_yb_EG_sim.py']

# for i in range(25):
#     args = []
#     args.append('-bwidth')
#     x = 200_000 + 40_000*(i)
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

# # NOTE VARYING: photon collection efficiency
# tasks = []

# command = ['python3', 'main_yb_yb_EG_sim.py']

# for i in range(7):
#     args = []
#     args.append('-pce')
#     x = 0.1*(i+1)
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


# # NOTE VARYING: QFC_EFF
# tasks = []

# command = ['python3', 'main_yb_uW_EG_sim.py']

# for i in range(21):
#     args = []
#     args.append('-qfc_eff')
#     x = 0.2 + (0.04*i)
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


# # NOTE VARYING: QFC_NOISE
# tasks = []

# command = ['python3', 'main_yb_uW_EG_sim.py']

# for i in range(30):
#     args = []
#     args.append('-qfc_noise')
#     x = 0.001 + 0.002*(i)
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

# # # NOTE VARYING: uW_NOISE
# tasks = []

# command = ['python3', 'main_yb_uW_EG_sim.py']

# for i in range(20):
#     args = []
#     args.append('-uw_noise')
#     x = 0.005*(i+1)
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


# # NOTE VARYING: uW efficiency
# tasks = []

# command = ['python3', 'main_yb_uW_EG_sim.py']

# for i in range(20):
#     args = []
#     args.append('-uw_efficiency')
#     x = 0.05*(i+1)
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

# # NOTE VARYING: transmon coherence
# tasks = []

# command = ['python3', 'main_yb_uW_EG_sim.py']

# for i in range(20):
#     args = []
#     args.append('-uw_coherence')
#     x = 10_000_000 + 30_000_000*(i+1)
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



# NOTE VARYING: coherence time linear network
tasks = []

command = ['python3', 'main_het_net_sim.py']

multiplier = [25, 50, 100, 200, 400, 600, 800, 1000]

for m in multiplier:
    args = []
    args.append('-uw_coherence')
    x = 10_000_000*m
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