
"""
Citation notice:

If you use this model, please cite:
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645

"""

import numpy as np


'''Function for efficiency variation depending on SOC'''

def eta(soc, c_rate, coeff):
    
    [p00, p10, p01, p20, p11, p02, p21, p12, p03] = coeff
    
    x = soc
    y = c_rate
    
    eta = p00 + p10*x + p01*y + p20*x**2 + p11*x*y + p02*y**2 + p21*x**2*y + p12*x*y**2 + p03*y**3
    
    return eta/100


'''Battery operation according to input power'''
def battery_operation(i, P_RES, P_goal, Capacity, SOC_old, kWh_factor):
    
    # https://doi.org/10.1016/j.jclepro.2021.129753
    SOC_max = 0.95
    SOC_min = 0.15
    C_rate_C_max = 1
    C_rate_D_max = 3
    
    eta_c = 0.995
    eta_d = 0.995
    
    Cap_actual = Capacity 
    
    P_bess_target = P_RES - P_goal  # the battery must compensate the mismatch between the RES power production and the power target   
    
    
    #Power excess, BESS charge
    if P_bess_target > 0:    
        
        P_max_C_rate   =  C_rate_C_max * Cap_actual                                                          # maximum power according to c-rate limitation
        P_max_SOC      =  (SOC_max - SOC_old)*Cap_actual*kWh_factor * eta_c    # maximum power according to SOC limitation
        
        P_bess = min(P_bess_target, P_max_C_rate, P_max_SOC)
        
        SOC_new = SOC_old + (P_bess/kWh_factor)/(Cap_actual) * eta_c
        
        P_output = P_RES - P_bess
        
        
    #Power deficit, BESS discharge
    else:
        
        P_max_C_rate   =  C_rate_D_max * Cap_actual                                                           # maximum power according to c-rate limitation
        P_max_SOC      =  (SOC_old - SOC_min)*Cap_actual*kWh_factor / eta_d     # maximum power according to SOC limitation
        
        P_bess = min(abs(P_bess_target), P_max_C_rate, P_max_SOC)
        
        SOC_new = SOC_old - ((P_bess/kWh_factor)/(Cap_actual)) / eta_d
        
        P_output = P_RES + P_bess
        
    return P_output, SOC_new






    
    
    