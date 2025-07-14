import time
from subprocess import Popen, PIPE

def get_output(p: Popen):
    stderr = p.stderr.readlines()
    if stderr:
        for line in stderr:
            print(line)

parameters = {1.0: 100, 0.5: 100, 0.25: 100, 0.1: 100, 0.05: 25, 0.025: 10}
# parameters = {0.05: 25}

tasks = []

command = ['python3', 'main_yb_yb_EG_sim.py']

for key in parameters.keys():
    args = []
    args.append('-eff')
    args.append(str(key))
    args.append('-n')
    args.append(str(parameters[key]))
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

# alternative runner for retrap
# for i in range(40):
#     args = []
#     args.append('-eff')
#     args.append(str(0.5))
#     args.append('-n')
#     args.append(str(100))
#     args.append('-retrap')
#     args.append(str(5*(i+1) + 5))
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

