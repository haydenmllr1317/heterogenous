import numpy as np

def ent_p(collection_p,transmission_p, detection_p, right_state_p):
    return right_state_p*((collection_p*transmission_p*detection_p)**2)

def time_to_ent(tweezer_prep_time, prep_number, entanglement_p, emission_t):
    return ((np.ceil(1/(prep_number*entanglement_p))*tweezer_prep_time) + (emission_t/entanglement_p))


print('p1 = 1')
print('P')
print(str(ent_p(1*(34.39/128),.997,.8,.5)))
print('t')
print(str(time_to_ent(.5, 128, ent_p(1*(34.39/128),.997,.8,.5), .0014)))
print('p1 = .5')
print('P')
print(str(ent_p(.5*(34.39/128),.997,.8,.5)))
print('t')
print(str(time_to_ent(.5, 128, ent_p(.5*(34.39/128),.997,.8,.5), .0014)))
print('p1 = .25')
print('P')
print(str(ent_p(.25*(34.39/128),.997,.8,.5)))
print('t')
print(str(time_to_ent(.5, 128, ent_p(.25*(34.39/128),.997,.8,.5), .0014)))
print('p1 = .1')
print('P')
print(str(ent_p(.1*(34.39/128),.997,.8,.5)))
print('t')
print(str(time_to_ent(.5, 128, ent_p(.1*(34.39/128),.997,.8,.5), .0014)))
print('p1 = .05')
print('P')
print(str(ent_p(.05*(34.39/128),.997,.8,.5)))
print('t')
print(str(time_to_ent(.5, 128, ent_p(.05*(34.39/128),.997,.8,.5), .0014)))
print('p1 = .025')
print('P')
print(str(ent_p(.025*(34.39/128),.997,.8,.5)))
print('t')
print(str(time_to_ent(.5, 128, ent_p(.025*(34.39/128),.997,.8,.5), .0014)))