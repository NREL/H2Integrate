# from smop.libsmop import *
import copy
import numpy as np
import random
import pandas as pd
import pandapower as pp
import pandapower.converter as pc
import matplotlib.pyplot as plt
# import pypower as pp
from pandapower.plotting.plotly import simple_plotly
from pandapower.plotting.plotly import pf_res_plotly
# VoltCont_Alg_Paper.m

# This file is voltage control without integrating the duals.

# addpath matpower4.1\matpower4.1;
# addpath(genpath('./'));
# mpopt=mpoption('OUT_ALL',0,'VERBOSE',0)
from define_powerflow_constants import *
mpc = pc.from_mpc('case6.mat', f_hz=50, validate_conversion=True)
num_bus = 5
L = np.array([[0,1,0,0,1],[1,0,1,0,0],[0,1,0,1,0],[0,0,1,0,0],[1,0,0,0,0]])
Vmin = 0.94
VMAX = 1.02
# generators and loads
gen = [1, 5]
num_gen = 2
loads = [2,3,4]
num_loads = 3
# control limits
x_max = ([[VMAX],[10],[10],[10],[VMAX]])
x_min = ([[0.97],[- 20],[- 20],[- 20],[0.97]])
# fixing rand seed
#*Differs from matlab/matpower
random.seed(128)
# augmenting reactive power demand to have a voltage violation
#*Differs from Matlab/Matpower Code. Loads are in mpc.load, not mpc.bus
# mpc.bus[:,QD] = mpc.bus(:,QD)*1.6*np.random(5,1)
# mpc.load['q_mvar'] = mpc.load['q_mvar'] * 1.6 * np.random.rand((len(mpc.load['q_mvar'])),1)
print("mpc.load before modification:")
print(mpc.load)
# mpc.load['q_mvar'] = mpc.load['q_mvar'] * 1.6 * [random.uniform(0,1) for x in range(0,len(mpc.load['q_mvar']))]
mpc.load['q_mvar'] = [140.979958318168, 127.967453454248, 139.101693580060]
print("mpc.load after modification:")
print(mpc.load)
# # Alg parameters
T = 100
lamb_M = np.zeros((5,T))
volt = np.zeros((5, T))
x = np.zeros((5, T))
x[0][0] = 1
x[4][0] = 1
xtil = copy.deepcopy(x)

# setting alg parameters
eta1 = 2 * np.array([[1],[1],[1],[10],[2]])
eta2 = 0.1 * np.array([[1],[10],[10],[10],[10]])
eta3 = 0.1 * np.array([[10],[1],[1],[1],[1]])
# vectors of function values
F_t = np.zeros((5,T))

# running the first PF to have initial conditions
mpc_result = pp.runpp(mpc)
#print element tables
print("-------------------")
print("  ELEMENT TABLES   ")
print("-------------------")

print("net.bus")
print(mpc.bus)

print("\n net.trafo")
print(mpc.trafo)

print("\n net.line")
print(mpc.line)

print("\n net.load")
print(mpc.load)

print("\n net.ext_grid")
print(mpc.ext_grid)

#print result tables
print("\n-------------------")
print("   RESULT TABLES   ")
print("-------------------")

print("net.res_bus")
print(mpc.res_bus)

print("\n net.res_trafo")
print(mpc.res_trafo)

print("\n net.res_line")
print(mpc.res_line)

print("\n net.res_load")
print(mpc.res_load)

print("\n net.res_ext_grid")
print(mpc.res_ext_grid)
#*Differs from matpower
# volt[:, 1] = mpc.bus(VM)
volt[:,0] = mpc.res_bus['vm_pu']
#Run for timesteps
# F_t = pd.DataFrame()
F_t = np.array(np.zeros((5,1)))
empty_mat_5x5 = np.copy(np.zeros((5,5)))
eta1_diag = np.copy(empty_mat_5x5)
eta2_diag = np.copy(empty_mat_5x5)
eta3_diag = np.copy(empty_mat_5x5)
np.fill_diagonal(eta1_diag, eta1)
eta2_diag = eta2_diag
np.fill_diagonal(eta2_diag, eta2)
eta3_diag = eta3_diag
np.fill_diagonal(eta3_diag, eta3)
for tt in range(2, T):
    # value of f and g
    f_t_step = np.zeros((5,1))
    for load in loads:
        print("Voltage for load {} is {}".format((load-1),volt[(load-1), (tt-2)]))
        if volt[(load-1),(tt-2)] < Vmin:
            f_t_step[(load-1)] = Vmin - volt[(load-1), (tt-2)]
            print(f_t_step)
    F_t = np.append(F_t, f_t_step.tolist(),1)
    test_1 = x[:, tt - 2]
    test_2 = eta1_diag
    test_3 = f_t_step
    test_4 = eta2_diag
    test_5 = L
    test_6 = lamb_M[:, (tt - 2)]

    # Computation of control inputs
    # xtil[:,tt-1] = x[:,tt-2] + eta1_diag * (f_t_step + eta2_diag * L * lamb_M[:,(tt-2)])
    eq_pt1 = np.dot(L, lamb_M[:, [(tt - 2)]]) #The bracket index syntax here is really important to recast ndarray vector to 2D
    eq_pt2 = np.dot(eta2_diag, eq_pt1)
    eq_pt3 = np.add(f_t_step, eq_pt2)
    eq_pt4 = np.dot(eta1_diag, eq_pt3)
    eq_end = np.add(x[:, [tt - 2]], eq_pt4) #The bracket index syntax here is really important to recast ndarray vector to 2D
    xtil[:, [tt - 2]] = eq_end

    # Lagrange Multipliers-like update
    test_b_1 = eta3_diag
    test_b_2 = xtil[:, [tt-1]] #The bracket index syntax here is really important to recast ndarray vector to 2D
    test_b_3 = x_max
    test_b_4 = xtil[:, [tt-1]] - x_max #The bracket index syntax here is really important to recast ndarray vector to 2D
    lamb_M[:,[tt-1]] = np.maximum(0, np.dot(eta3_diag, (xtil[:, [tt-1]] - x_max)))
#
    # Projection
    x[:, [tt-1]] = xtil[:, [tt-1]]

    for nn in range(0, 4):
        if x[nn,tt-1] > x_max[nn][0]:
            x[nn,tt-1] = x_max[nn][0]
        if x[nn,tt-1] < x_min[nn][0]:
            x[nn,tt-1] = x_min[nn][0]

    # Actuation
    for load in loads:
        #mpc.gen[loads(ll), QG] in matpower here might be most similar to mpc.res_bus in pandapower
        # Qg (index=3), reactive power output (MVAr)
        # load/loads is just indexing to the loads (as opposed to the other
        # bus elements)
        mpc.res_bus['q_mvar'][load-2] = x[load-1, tt-1]
        # mpc.load['p_mw'][load-2] = x[load-1, tt-1]
        # mpc.gen['p_mw'] = x[load-1, tt-1]
        # mpc.ext_grid['vm_pu'][load-2] = x[load-1, tt-1]
        # mpc.res_ext_grid['q_mvar'][load-2] = x[load-1, tt-1]
        # mpc.res_load['p_mw'][load - 2] = x[load - 1, tt - 1]
    # Generators are index 1 and 5 (0 and 4 python). Need to set the vm_pu value for the generators
    # Vg(index=6), voltage magnitude setpoint(p.u.)
    for gg in range(0, num_gen):
        mpc.gen['vm_pu'][0] = x[gen[gg]-1, tt-1]
        mpc.res_gen['vm_pu'][0] = x[gen[gg]-1, tt-1]

    # mpc.res_gen['vm_pu'][0] = 1
    # mpc.ext_grid['vm_pu'][0] = 0.93
    pp.runpp(mpc, init_vm_pu="results")
    volt[:, tt-1] = mpc.res_bus['vm_pu']

    print(mpc.res_bus['p_mw'][0])

print('Stop and debug')

#
# ax, fig = plt(volt(1, :),'b')
# #
# # plot(volt(2, arange()),'r')
# # plot(volt(3, arange()),'r')
# # plot(volt(4, arange()),'r')
# # plot(volt(5, arange()),'b')
# #
# # legend('generators','loads')
# # ylabel('Voltages')
# # contr_max = copy(x_max)
# # contr_max[1,1]=VMAX - 1
# # contr_max[end(),1]=VMAX - 1
# # scale= dot(concat([[- 1],[0],[0],[0],[- 1]]),ones(1,T))
# # contr_eff=(x + scale) / (dot(contr_max,ones(1,T)))
# # figure
# # plot(contr_eff.T)
# # legend('bus 1','bus 2','bus 3','bus 4','bus 5')
# # figure
# # plot(volt.T)
# # legend('bus 1','bus 2','bus 3','bus 4','bus 5')