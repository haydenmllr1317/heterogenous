from numpy import random as rm
from math import e

def f(x):
    return (0.86)*(.9824)**x

def g(x):
    return (0.86)*(e**(-x/40))

n = 100
count = 0

for j in range(n):
    for i in range(128):
        p = f(i)
        if rm.rand() <= p:
            count += 1

avg = count/n

print(avg)
