import time
from subprocess import Popen, PIPE

def get_output(p: Popen):
    stderr = p.stderr.readlines()
    if stderr:
        for line in stderr:
            print(line)

# parameters = {1.0: 200, 0.5: 200, 0.25: 200, 0.1: 100, 0.05: 60, 0.025: 30}
# # parameters = {0.05: 25}

tasks = []

command = ['python3', 'main_yb_yb_EG_sim.py']

# for key in parameters.keys():
#     args = []
#     args.append('-eff')
#     args.append(str(key))
#     args.append('-n')
#     args.append(str(parameters[key]))
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

numlist = [10, 100, 1000, 10000, 100000]
# alternative runner for retrap
for element in numlist:
    args = []
    args.append('-eff')
    args.append(str(0.25))
    args.append('-n')
    args.append(str(100))
    # args.append('-retrap')
    # args.append(str(i+5))
    args.append('-darkc')
    args.append(str(element))
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

