
"""
Citation notice:

If you use this model, please cite:
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645

"""

import pandas as pd
import numpy as np
import pickle


# from MODEL_battery_NMC_nodeg import battery_operation
from MODEL_battery_NMC_simplified import battery_operation

#%%
###########################################################################################################################################
'MAIN'

def extra_simplified_sim(df_data, s, BESS_size, EL_CF, FC_CF):
    
    
    l_compr_ms = 1.1840067369329885
    kWh_factor = 60

    
    P_wind = df_data['wind_power']
    P_pv = df_data['PV_power']
    P_load = df_data['load']
    T_ext = df_data['temperature']

    counterlist = []

    # print(s)
    
    EL_size = s[0]
    FC_size = s[1]
    # BESS_size = s[2] * 10
    Tank_size = s[3]
    PV_upgrade = s[4]
    
    if EL_size == 0:
        H2_storage = False
    else:
        H2_storage = True
    
    'power fluxes'
    #available power form RES     
    P_RES = P_wind + P_pv * ( 1 + PV_upgrade / 16)

            
    'ALK electrolyzer and PEM FC'

    'ELECTROLYZER'
    EL_cell_power = 9.45         #kW
    #number of availabe cells
    EL_cell_number = EL_size
    #electrolyzer stack nominal pwoer [kW]
    EL_P_nom = EL_cell_number * EL_cell_power 
    #power required by the alkaline electrolyzer to start the hydrogen production
    EL_P_min = 0.2 * EL_P_nom
    
    'FUEL CELL'
    FC_cell_power = 13.57         #kW
    #number of availabe cells
    FC_cell_number = FC_size
    #electrolyzer stack nominal pwoer [kW]
    FC_P_nom = FC_cell_number * FC_cell_power
    #power required by the alkaline electrolyzer to start the hydrogen production
    FC_P_min = 0.01 * FC_P_nom
    
    'BESS'
    #battery capacity [kWh]
    BESS_capacity = BESS_size

    # initial SOC hypotesis
    BESS_SOC = 0.4
    
    #charge and discharge C-rate   
    
    #high pressure tank capacity [kg]
    tank = Tank_size
    H2_buffer_list = [0.1*tank]
    if tank == 0:
        H2_buffer_list = [0]
    H2_buffer = H2_buffer_list[0]
    
    'TANK - low pressure (30 bar)'  
    #low pressure tank capacity [kg]
    lp_tank = 10
    H2_lp_buffer = 0
    counter = 0
    
    # time_to_compress = 30 #np.ceil(30 * s[4]/20)  # [min]
    time_to_compress = lp_tank / (60/kWh_factor)   # [min] 1kg/min compression
    # times_output.append(s[6])
    
#%%
    'H2 request'
    EL_H2_prod = 0
    E_load_cumulative = 0
    
    # Cumulative variables to track the variation of quantities in time
    EL_P_recieved_cumulative = 0
    EL_H2_prod_cumulative = 0
    EL_H2_prod_y_cumulative = 0
    
    C_H2_prod_cumulative = 0
    C_P_cumulative = 0
    
    FC_P_delivered_cumulative = 0
    FC_H2_req_cumulative = 0
    
    P_BESS_excess_cumulative = 0
    P_BESS_deficit_cumulative = 0
    P_excess_cumulative = 0
    P_deficit_cumulative = 0    
    
    'for loop for each timestep of the timeframe'
    for i in range(len(P_RES)):
        
        P_compressor = l_compr_ms * (lp_tank / time_to_compress) * kWh_factor 
    
        #########################################################
        'target power'
        # if the battery supports the load
        if counter != 0:  # If the counter is not equal to 0, the compressor will work so extra load
            P_requested = P_load.iloc[i] + P_compressor
    
        else:  # If the counter is 0, the low-pressure tank is not full yet so the compressor is off
            P_requested = P_load.iloc[i]
            
        E_load_cumulative += P_load.iloc[i]
    
        #########################################################
        'battery operation'
        P_BESS, BESS_SOC_new = battery_operation(i, P_RES.iloc[i], P_requested, Capacity=BESS_capacity,
                                                  SOC_old=BESS_SOC, kWh_factor=kWh_factor)
    
        # BESS parameters tracking
        BESS_SOC = BESS_SOC_new
    
        #########################################################
        'residualP_RESmismatch'
    
        if P_BESS > P_requested:
            P_BESS_excess = P_BESS - P_requested
            P_BESS_deficit = 0
    
            if counter != 0:
                H2_to_c = lp_tank / time_to_compress  # H2 to be compressed min
                counter = counter - 1  # The compressor will work until the counter is back at 0.
                H2_lp_buffer = H2_lp_buffer - lp_tank / time_to_compress  # Amount of H2 left in low-pressure tank
    
            else:
                H2_to_c = 0
                P_compressor = 0
    
        else:
            P_BESS_excess = 0
            P_BESS_deficit = P_requested - P_BESS
            H2_to_c = 0
            P_compressor = 0
    
        P_BESS_excess_cumulative += P_BESS_excess
        P_BESS_deficit_cumulative += P_BESS_deficit   
    
        if H2_storage == True: 
    
            #########################################################
            'eletrolyzer activation'
    
            # H2 production calculation in the given minute
            if P_BESS_excess > EL_P_min:
                if P_BESS_excess < EL_P_nom:
                    EL_P_given = P_BESS_excess
                else:
                    EL_P_given = EL_P_nom
    
                EL_H2_prod = EL_P_given * EL_CF / kWh_factor
    
                # produce only the hydrogen mass that fits in the lp_tank
                if EL_H2_prod + H2_lp_buffer > lp_tank:
                    EL_H2_prod = lp_tank - H2_lp_buffer
                    EL_P_given = EL_H2_prod / EL_CF * kWh_factor
                    # counter = time_to_compress # compressor starts working for the given amount of time when the tank is full.
    
                if H2_to_c + H2_buffer > tank:
                    H2_to_c = (tank - H2_buffer) if (tank - H2_buffer) > 0 else 0
                    EL_H2_prod = 0
                    EL_P_given = 0
    
            else:
                EL_H2_prod = 0
                EL_P_given = 0
    
            # trend of the power fed to the electrolyzer
            EL_P_recieved_cumulative += EL_P_given
            # H2 produced at each timestep
            EL_H2_prod_cumulative += EL_H2_prod
            # annual hydrogen yield
            EL_H2_prod_y_cumulative += EL_H2_prod  
    
            # H2 produced at each timestep during compression
            C_H2_prod_cumulative += H2_to_c
    
            C_P_cumulative += P_compressor
    
            #########################################################
            'Excess power from RES, not converted to H2'
            P_excess_cumulative += P_BESS_excess - EL_P_given        
            ########################################################
    
    
            #########################################################
            'fuel cell activation'
    
            # H2 consumption calculation in the given minute
            if P_BESS_deficit > FC_P_min:
    
                if P_BESS_deficit < FC_P_nom:
                    FC_P_delivered = P_BESS_deficit
                else:
                    FC_P_delivered = FC_P_nom
    
                FC_H2_req = FC_P_delivered * FC_CF / kWh_factor
    
                # conversion in electricity of the residual hydrogen in the tank
                if (H2_buffer + H2_lp_buffer) < FC_H2_req:
                    FC_H2_req = H2_buffer + H2_lp_buffer
                    FC_P_delivered = (H2_buffer + H2_lp_buffer) / FC_CF * kWh_factor
    
            else:
                FC_H2_req = 0
                FC_P_delivered = 0
    
            # trend of the power delivered by the fuel cell
            FC_P_delivered_cumulative += FC_P_delivered
            # H2 consumed at each timestep
            FC_H2_req_cumulative += FC_H2_req
    
    
    
            #########################################################
            'Deficit power, not covered by H2'
            P_deficit_cumulative += P_BESS_deficit - FC_P_delivered
            #########################################################
            'tank management'
            H2_lp_buffer = H2_lp_buffer + EL_H2_prod
    
            if H2_lp_buffer / lp_tank > 0.9:
                counter = time_to_compress  # compressor starts working for the given amount of time when the tank is full.
    
    
            H2_buffer = H2_buffer + H2_to_c
    
            if H2_lp_buffer > FC_H2_req:
                H2_lp_buffer = H2_lp_buffer - FC_H2_req
    
            else:
                H2_buffer = H2_buffer - (FC_H2_req - H2_lp_buffer)
                H2_lp_buffer = 0
    
            #########################################################
    
        else:
            P_excess_cumulative += P_BESS_excess  
            P_deficit_cumulative += P_BESS_deficit
    

    'Data saving after the for loop'        
    # E_RES = (sum(P_RES)/kWh_factor)/1000                                #[MWh]  available energy from RES after BESS
    E_load = ( E_load_cumulative / kWh_factor ) / 1000                              #[MWh]  total energy required by load
    
    #excess and deficit Energy RES
    # P_mismatch = P_RES - P_load                                             #[kW] power mismatch between RES and load
    # E_deficit_RES = - sum(p for p in P_mismatch if p < 0)/kWh_factor/1000   #[MWh]  deficit energy with initial RES
    # E_excess_RES = sum(p for p in P_mismatch if p > 0)/kWh_factor/1000      #[MWh]  excess energy with initial RES
    # E_to_load_RES = E_load - E_deficit_RES                                  #[MWh]  energy feeding the load with initial RES
    
    #excess and deficit with BESS
    E_deficit_BESS = ( P_BESS_deficit_cumulative / kWh_factor)/1000          #[MWh]  deficit energy after BESS storage
    E_excess_BESS = ( P_BESS_excess_cumulative / kWh_factor)/1000            #[MWh]  excess energy after BESS storage
    E_to_load_BESS = E_load - E_deficit_BESS                             #[MWh]  energy feeding the load after BESS

    E_comp = (C_P_cumulative / kWh_factor)/1000                             #[MWh]  electrical en absorbed by compressor
    E_RES_to_H2 = (EL_P_recieved_cumulative/kWh_factor)/1000              #[MWh]  electrical en converted to hydrogen

    #excess and deficit with H2
    E_deficit_H2 = (P_deficit_cumulative / kWh_factor)/1000                 #[MWh]  deficit energy after H2 storage
    E_excess_H2 = (	P_excess_cumulative / kWh_factor)/1000                   #[MWh]  excess energy after H2 storage
    E_to_load_H2 = E_load - E_deficit_H2                                 #[MWh]  energy feeding the load after H2
    

    'output'
    output = pd.DataFrame()
    output['BESS[MWh]'] = [BESS_capacity]
    output['SOH_final'] = [1]

    output['PV_power[kWp]'] = [160 * (1 + PV_upgrade/16)]
    output['EL_n_cells'] = [EL_cell_number]
    output['FC_n_cells'] = [FC_cell_number]
    output['HP_tank[kg]'] = [tank]
    output['LP_tank[kg]'] = [lp_tank]

    output['EL_CF[kg/MWh]'] = [EL_CF * 1000]
    output['FC_CF[kg/MWh]'] = [FC_CF * 1000]

    output['H2_prod_EL[kg]'] = [EL_H2_prod_cumulative]
    output['H2_Comp [kg]']  = [C_H2_prod_cumulative]

    output['E_RES[MWh]']=           [0] # [E_RES]
    output['E_deficit_RES[MWh]']=   [0] # [E_deficit_RES]
    output['E_excess_RES[MWh]']=    [0] # [E_excess_RES]
    output['RES_SC[%]'] =           [0] # [E_to_load_RES/E_load * 100]

    output['E_BESS_deficit[MWh]']= [E_deficit_BESS]
    output['E_BESS_excess[MWh]'] = [E_excess_BESS]
    output['BESS_SC[%]'] = [E_to_load_BESS/E_load * 100]

    output['E_to_H2[MWh]'] = [E_RES_to_H2]
    output['E_comp[MWh]'] = [E_comp]

    output['E_H2_deficit[MWh]']= [E_deficit_H2]
    output['E_H2_excess[MWh]'] = [E_excess_H2]
    output['H2_SC[%]'] = [E_to_load_H2/E_load * 100]
    
    
    
    return output

