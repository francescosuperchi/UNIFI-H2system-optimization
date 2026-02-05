
from collections import deque, defaultdict
import numpy as np
import functools
import math  
from scipy import interpolate
import rainflow


'''Function for efficiency variation depending on SOC'''

def eta(soc, c_rate, coeff):
    
    [p00, p10, p01, p20, p11, p02, p21, p12, p03] = coeff
    
    x = soc
    y = c_rate
    
    eta = p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2 + p21*x**2*y + p12*x*y**2 + p03*y**3
    
    return eta/100


'''Battery operation according to input power'''
def battery_operation(i, P_RES, P_goal, Capacity, SOC_old, SOH_old, Degr, SOC_day, C_rate_day, kWh_factor):
    
    # https://doi.org/10.1016/j.jclepro.2021.129753
    SOC_max = 0.95
    SOC_min = 0.15
    C_rate_C_max = 1
    C_rate_D_max = 3
    
    # https://ieeexplore.ieee.org/document/8770143 - 10.1109/TPWRS.2019.2930450
    coeff_c = [100.968, -0.259233, -6.41535, 0.0799907, 1.84443, 0.255217, -0.563289, -0.171151, 0.0549735]
    coeff_d = [100.147, 0.0997555, -6.07639, -0.24408, 0.150757, 0.0434057, 0.879053, -0.0354527, -0.00266084]
    
    Cap_actual = Capacity * SOH_old 
    
    P_bess_target = P_RES - P_goal  # the battery must compensate the mismatch between the RES power production and the power target   
    
    
    #Power excess, BESS charge
    if P_bess_target > 0:    
        C_rate_D = 0
        
        P_max_C_rate   =  C_rate_C_max * Cap_actual                                                          # maximum power according to c-rate limitation
        P_max_SOC      =  (SOC_max - SOC_old)*Cap_actual*kWh_factor * eta(SOC_old, C_rate_C_max, coeff_c)    # maximum power according to SOC limitation
        
        P_bess = min(P_bess_target, P_max_C_rate, P_max_SOC)
        
        C_rate_C = np.abs( P_bess / (Cap_actual) ) 
        SOC_new = SOC_old + (P_bess/kWh_factor)/(Cap_actual) * eta(SOC_old, C_rate_C, coeff_c)
        
        P_output = P_RES - P_bess
        
        
    #Power deficit, BESS discharge
    else:
        C_rate_C = 0
        
        P_max_C_rate   =  C_rate_D_max * Cap_actual                                                           # maximum power according to c-rate limitation
        P_max_SOC      =  (SOC_old - SOC_min)*Cap_actual*kWh_factor / eta(SOC_old, C_rate_D_max, coeff_d)     # maximum power according to SOC limitation
        
        P_bess = min(abs(P_bess_target), P_max_C_rate, P_max_SOC)
        
        C_rate_D = np.abs( P_bess / (Cap_actual) ) 
        SOC_new = SOC_old - ((P_bess/kWh_factor)/(Cap_actual)) / eta(SOC_old, C_rate_D, coeff_d)
        
        P_output = P_RES + P_bess


    'daily degradation'
    if (i+1) % kWh_factor*24 == 0:  
        Degr = Battery_degradation_day(SOC_day, Degr)

    SOH_new = 1 - 0.3 * Degr
        
    return P_output, SOC_new, SOH_new, Degr, C_rate_C, C_rate_D


'''Daily battery degradation'''
def Battery_degradation_day(SOC_day, Degr):
    
    # https://doi.org/10.1016/j.apenergy.2018.08.058
    a = 1512.45
    b = - 0.968423
    
    #count cycles perfoemd at each DOD
    rainflow_out = rainflow.count_cycles(SOC_day, ndigits=3)
    
    min_range = 0.01

    for i,j in rainflow_out:
        
        #DoD - Cycles function starts from DOD = 5%
        if i > min_range:
            
            DoD_i = i
            EoL_i = a * DoD_i ** b 
            # damage is number of cycles at a certain DOD / number of cycles at that DOD that brings to EOL
            Degr += j/EoL_i
                
    return Degr

    




    
    
    