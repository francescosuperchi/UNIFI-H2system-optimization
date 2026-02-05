
"""
Citation notice:

If you use this model, please cite:
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645

"""

import numpy as np
import math
from scipy import interpolate

#%%

#polarization curve derived from the public datasheet of a PEM fuel cell
I_array       = [0,40,80,120,160,200,230, 250] 
V_array_ideal = [94,78,73,69,66,62,59, 57] 

def FC_model(T_FC, h_work_tot, n_stacks, kWh_factor, V_array_ideal = V_array_ideal):
    
    '''
    conv_factor : Efficienza di conversione Power to H2.
    
    conv_factor : efficiency of conversion Power to H2.
    f_i_V : Current to voltage function.
    f_H2_i : H2 production to current function.
    V_array : Array containing Min e max voltage.
    
    full description in https://doi.org/10.1016/j.apenergy.2024.124645
    
    '''    
    n_cells = 96
    FC_CF_nom = 59 / 1000         # kg/kWh 
        
    T_operation = 60              # °C
    V_degr = 5 * 10 ** -6  * n_cells      # uV/h time degradation for dynamic operation   https://doi.org/10.1016/j.ijhydene.2022.04.011
    V_T    = 5 * 10 ** -4   * n_cells      # mV/°C temperature degradation                https://doi.org/10.3390/en13123144

    #voltage decreases for usage in time and for opeartion at temeprature below nominal conditions
    V_array     = [(V - V_degr * h_work_tot - V_T * (T_operation - T_FC)) for V in V_array_ideal] 
    
    H2_array    = [(I_array[i] * V_array_ideal[i] * n_stacks / 1000 * FC_CF_nom ) for i in range(len(V_array))]  #stack power (kW) * CF ideal
    
    FC_conv_factor = n_stacks * (max(I_array)*min(V_array))/1000 / max(H2_array)    # P/H2 flow [kW/(kg/h) = kWh/kg]     
    
    conv_factor = 1/FC_conv_factor     # [kg/kWh] hydrogen needed for 1kWh of electrical energy
        
    f_i_V  = interpolate.interp1d(I_array,V_array)                 
    f_H2_i = interpolate.interp1d([item/ kWh_factor for item in H2_array],I_array)  
    
    return conv_factor, f_i_V, f_H2_i


#%%

def FC_transit(H2_req,f_i_V, f_H2_i, T_FC, n_stacks, T_ext, kWh_factor):
    
    '''
    Themal model: exothermic reaction (heat production from thermal lossess DeltaV = V-Vtn)  
    T_FC : fuel cell temperature
    
    full description in https://doi.org/10.1016/j.apenergy.2024.124645
    
    '''
    
    n_stacks_design = 96                            #number of stacks
    L_design = 0.58*(n_stacks_design/6)             # length of stack
    W_design = 0.196*3                              # width of stack
    H_design = 0.288*2                              # [m] hight of stack
    
    r1_design = 0.5*(4*W_design*H_design)/(2*H_design+2*W_design)                   # [m] equivalent radius (assume box is pipe)
    
    SF = n_stacks/n_stacks_design        # scaling factor
    
    L = L_design * SF
    
    pi = math.pi
    op_time = (60*60)/(kWh_factor)       # [s]  tempo del transitorio termico (1 min)
    T_op = 60                          # [°C] operational temperature

    
    T_amb = T_ext
    
    V_tn = 1.48                        # [V]  voltage thermoneutral
    
    'geometry'
    r1 = r1_design         
    s1 = 0.004                          # [m] thickness around fuel cell
    
    r3 = 1            # [m] radius air gap

    s2 = 0.2     # [m]     thickness isolation material
    
    'coefficeints'

    h2 = 10           # [W/ m^2K]   convection between fuel cell and container
    h3 = 20           # [W/ m^2K]   convection container and ambient
    
    k1 = 52           # [W/ mK] conduction steel     
    k2 = 0.05    # [W/ mK] conduction isolation material 
        
    
    'electrolyte'
    m_FC = (L * r1 * r1 * pi * 2240)/5 # / 2 # [kg] mass of fuel cell
    c_FC = 710                         # [J/kg*K]   heat capacity fc

    b = k1*2*pi*L/np.log((r1 + s1)/r1)
    c = h2*2*pi*(r1 + s1)*L
    d = h2*2*pi*r3*L
    e = k2*2*pi*L/np.log((r3 + s2)/r3)
    f = h3*2*pi*(r3 + s2)*L
    
    q_lost = (T_FC - T_amb) / (1/b + 1/c + 1/d + 1/e + 1/f) # [W] thermal power lost to the environment
    

    if H2_req > 0:  
        I_op = f_H2_i(H2_req)
        V_op = f_i_V(I_op)
        q_gain = n_stacks * (V_tn-V_op)*I_op*1000     # [V]*[kA]*1000 = [V]*[A] = [W] produce thermal power
                
        Tx = T_FC + (op_time / (m_FC * c_FC)) * abs(q_gain - q_lost)
    
        if Tx > T_op:
            Tx = T_op

    else:
        Tx = T_FC - (op_time / (m_FC * c_FC)) * q_lost
    
    return Tx


    
    
    
    
    
    
    
