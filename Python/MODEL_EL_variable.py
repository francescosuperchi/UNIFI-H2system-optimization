
"""
Citation notice:

If you use this model, please cite:
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645

Electrolyzer model based on: https://doi.org/10.1016/j.renene.2023.03.077

"""

import numpy as np
import math
from scipy import interpolate

V_array_ideal = np.array([1.64,1.9])
i_array_ideal = np.array([2,10])              #current density [kA/m2]

def EL_model(T_el, h_work_tot, n_cells, kWh_factor, i_array_ideal = i_array_ideal, V_array_ideal = V_array_ideal):
    '''
    conv_factor : efficiency of conversion Power to H2.
    f_i_V : Current to voltage function.
    f_H2_i : H2 production to current function.
    V_array : Array containing Min e max voltage.
    
    full description in section 2.2.1 of https://doi.org/10.1016/j.renene.2023.03.077
    
    '''
    n_cells_design = 106               # number of cells in the 1MW stack
    SF = n_cells/n_cells_design        # scale factor of the configuration
    
    H2_design = 18         # [kg/h] nominal produced hydrogen flow from the 1MW module
    
    T_operation = 71
    V_degr = 3 * 10 ** -6     # uV/h time voltage increase
    V_T = 5 * 10 ** -3        # 5mV/°C cool down voltage increase
    S_cell = 0.5              # m^2 surface of cells


    #cell voltage = stack voltage / n_cells
    V_array     = V_array_ideal + V_degr * h_work_tot + V_T*(T_operation - T_el)

    #limit on the time degradation for cell voltage
    if max(V_array - V_T * (T_operation-T_el)) > 2.3:
        print('High voltage, new electrolyzer is needed')   
        
    #cell current = stack current 
    I_array     = i_array_ideal*S_cell     
    
    #H2 production array of the stack = n_cells * H2 production of a cell
    H2_array    = np.array([0, H2_design * SF])
    
    #link between cell current (= stack current) and cell voltage: polarization curve
    f_i_V = interpolate.interp1d(I_array,V_array)

    #link between stack H2 production and stack current (= cell current)                 
    f_H2_i = interpolate.interp1d(H2_array/kWh_factor,I_array)   
    
    #conversion factor calculation: H2 stack production / P stack consumption
    conv_factor = max(H2_array)/ (max(I_array) * max(V_array) * n_cells)      # [kg/kWh]    
    
    return conv_factor, f_i_V, f_H2_i, V_array


def EL_transit(H2_prod,f_i_V, f_H2_i, T_el, n_cells, T_ext, kWh_factor):
    
    '''
    Themal model: exothermic reaction (heat production from thermal lossess DeltaV = V-Vtn)  
    T_el : electrolyzer temperature
    
    full description in section 2.2.3 of https://doi.org/10.1016/j.renene.2023.03.077
    
    '''
    
    n_cells_design = 106               # number of cells in the 1MW module
    L_design = 3                       # [m] design length of the gas-liquid separator
    r1_design = 0.3                    # [m] internal radius
    
    SF = n_cells/n_cells_design        # scale factor della configurazione, lo applico al volume
    
    L = L_design * SF**(1/3)           # scale of the geometry accoring to the SF
    
    pi = math.pi
    op_time = (60*60)/(kWh_factor)       # [s]  simulation time in seconds
    T_op = 71                            # [°C] operating temperature
    # T_ext = 25                         # [°C] external temperature, activate in case 
        
    V_tn = 1.48                        # [V]  thermoneutral voltage
    
    'geometry'
    r1 = r1_design * SF**(1/3)          
    s1 = 0.004                          # [m] thickness of the electrolyzer container
    
    r3 = 1             # [m]  container internal radius
    s2 = 0.005         # [m] container thickness
    
    'heat coefficeints'
    h1 = 100          # [W/ m^2K]   internal convection between water (H2O + 30% KOH) - tank
    h2 = 10           # [W/ m^2K]   convection tank-container
    h3 = 20           # [W/ m^2K]   external convection container-air
    
    k1 = 52           # [W/ mK] steel tank conduction 
    k2 = 52           # [W/ mK] steel container conduction     
    
    'instulated container'
    insulation = True
    if insulation == True:
        s2 = 0.2     # [m]     insulation layer thickness

        k2 = 0.05    # [W/ mK] insulation layer conduction
        
    
    'electrolyte'
    m_elect = L * r1 * r1 * pi * 1000 / 2 # [kg] of H2O in gas-liquid separator (half water, half gas)
    c_elect = 4190                        # [J/kg*K]   water specific heat

    a = h1*2*pi*r1*L
    b = k1*2*pi*L/np.log((r1 + s1)/r1)   
    c = h2*2*pi*(r1 + s1)*L
    d = h2*2*pi*r3*L
    e = k2*2*pi*L/np.log((r3 + s2)/r3)
    f = h3*2*pi*(r3 + s2)*L
    
    q_lost = (T_el - T_ext) / (1/a + 1/b + 1/c + 1/d + 1/e + 1/f) # [W] thermal power lost to the environment

    if H2_prod > 0:  
        #stack current from H2 production
        I_op = f_H2_i(H2_prod)
        #cell voltage from cell current (= stack current)
        V_op = f_i_V(I_op)
        
        #thermal power generated form the stack
        q_gain = n_cells * (V_op-V_tn)*I_op*1000     # [V]*[kA]*1000 = [V]*[A] = [W] produce thermal power
                
        Tx = T_el + (op_time / (m_elect * c_elect)) * (q_gain - q_lost)
    
        if Tx > T_op:
            Tx = T_op

    else:
        Tx = T_el - (op_time / (m_elect * c_elect)) * q_lost
    
    return Tx
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
