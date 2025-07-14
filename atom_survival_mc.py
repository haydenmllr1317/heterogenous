from numpy import random as rm
from math import e

def f(x):
    return (.9708)**x

def g(x):
    return e**(-x/40)

n = 100
count = 0

for j in range(n):
    for i in range(128):
        # p = g(1)
        p = .9708
        if rm.rand() < p:
            # print(rm.rand())
            count += 1
        else:
            break

avg = count/n

print(avg)
