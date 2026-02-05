
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

#%%

'PLOTS'

fc_plots = False

if fc_plots == True:
    import matplotlib.pyplot as plt
    
    
    'funzioni ideali'
    I_array       = [0, 40,80,120,160,200,230,231 ]
    V_array_ideal = [94,78,73,69, 66, 62, 59, 58.9] 
    FC_CF_nom = 59 /1000
    n_stacks = 96             #current density [kA/m2]
    H2_array_ideal = [(I_array[i] * V_array_ideal[i] * n_stacks / 1000 * FC_CF_nom ) for i in range(len(V_array_ideal))]
    
    
    f_i_V_id = interpolate.interp1d(I_array,V_array_ideal) 
    f_H2_i_id = interpolate.interp1d(H2_array_ideal,I_array)
    x_i_id = np.arange(I_array[0],I_array[-1]+0.01, 0.01)
    x_H2_id = np.arange(H2_array_ideal[0],(H2_array_ideal[-1]), 0.01)
    y_i_id = f_H2_i_id(x_H2_id)
    y_v_id = f_i_V_id(x_i_id)
    
    #%%
    
    'ideal voltage curve'
    plt.figure(figsize = (6,4))
    plt.plot(x_i_id,y_v_id)
    plt.grid(alpha = 0.3)
    plt.ylabel('Voltage [V]') #,fontsize=15, labelpad=15,fontweight="bold")
    plt.xlabel('Current [A]') #,fontsize=15, labelpad=15,fontweight="bold")
    plt.title('Voltage vs Current density - ideal curve') #,fontsize=15,fontweight="bold")
    
        
    #%%
    
    'ideal h2 production curve'
    plt.figure(figsize = (6,4))
    plt.plot(x_H2_id,y_i_id)
    plt.grid(alpha = 0.3)
    plt.ylabel('Current [A]') #,fontsize=15, labelpad=15,fontweight="bold")
    plt.xlabel('H2 request per module [kg/h]') #,fontsize=15, labelpad=15,fontweight="bold")
    plt.title('Current vs $\mathregular{H_2}$ production - ideal curve') #,fontsize=15,fontweight="bold")

    
            
    #%%
    
    ''' curve di degradazione '''
    'temperature degradation'
    from colour import Color

    T_operation = 60
    # V_T = 5 * 10 ** -3        # 5mV/°C degradazione per raffreddamento
    
    V_T_cell = 5.13 * 10 ** -4        # 5mV/°C degradazione per raffreddamento

    V_T = V_T_cell * 96    

    color1 = Color("#05a3f7")

    colori = (list(color1.range_to("#f70521",7)))

    hex_list = list()

    for i in range(len(colori)):
        hex_list.append(str(colori[i]))   

    j=0
    
    plt.figure(figsize = (5,5))    # zoom (3,3)
    T_el = np.arange(10,61,10)
    # T_el = np.arange(50,61,2)

    for i in range(len(T_el)):
        V_degr_T = V_array_ideal - V_T*(T_operation - T_el[i])
        f_i_V = interpolate.interp1d(I_array,V_degr_T) 
        x_i = np.arange(I_array[0],I_array[-1]+1, 1)
        y_v = f_i_V(x_i)
        plt.plot(x_i,y_v, label= '%d °C' %(T_el[i]), color = hex_list[j])
        j = j + 1
    
    plt.grid(alpha = 0.3)
    legend_properties = {'size':8}
    # plt.legend(prop=legend_properties,edgecolor='black',framealpha=0.5, loc='upper right', ncol = 2) 
    plt.ylabel('Voltage [V]')
    plt.xlabel('Current [A]')
    plt.xlim(0,230)
    plt.ylim(0,95)
    
    # plt.xlim(90,100)
    # plt.ylim(67.5,72.5)
    
    #%%
    
    'time degradation' 
    V_degr_cell = 16 * 10 ** -6     # uV/h degradazione nel tempo
    
    V_degr = V_degr_cell * 96
    
    color1 = Color("blue")

    colori = (list(color1.range_to("brown",7)))

    hex_list = list()
    
    for i in range(len(colori)):
        hex_list.append(str(colori[i]))   

    j=0
    
    CF = 0.1
    
    plt.figure(figsize = (5,5))
    h_work_tot = np.arange(0,12*24*365 * CF, 2*24*365* CF)
    for i in range(len(h_work_tot)):
        V_degr_time = V_array_ideal - ( V_degr * h_work_tot[i] ) 
        f_i_V = interpolate.interp1d(I_array,V_degr_time) 
        x_i = np.arange(I_array[0],I_array[-1]+1, 1)
        y_v = f_i_V(x_i)
        plt.plot(x_i,y_v, label= '%d years' %(h_work_tot[i]/365/24 / CF),  color = hex_list[j])
        j = j + 1
    
    plt.grid(alpha = 0.3)
    legend_properties = {'size':8} #,'weight':'bold'.
    plt.legend(prop=legend_properties,edgecolor='black',framealpha=0.5, loc='upper right', ncol = 2)  #loc='lower left'
    plt.ylabel('Voltage [V]') #,fontsize=15, labelpad=15,fontweight="bold")
    plt.xlabel('Current [A]') #,fontsize=15, labelpad=15,fontweight="bold")
    plt.xlim(0,230)
    plt.ylim(0,95)


    
    #plt.title('Working time influence on Polarization curve') #,fontsize=15,fontweight="bold")
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
