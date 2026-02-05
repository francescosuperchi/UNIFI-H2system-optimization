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
from MODEL_EL_variable import EL_model,EL_transit
from MODEL_FC_variable import FC_model, FC_transit
from MODEL_battery_NMC import battery_operation
import time

'Power production, load and temperature data input'

counterlist = []
    
###########################################################################################################################################
'Compressor'
R = 8.314 # Universal gas constant [J / (mol * K)]
MM_h2 = 0.00216        # [kg/mol]
R_specific = R / MM_h2 # [J / (kg * K)]

T_1 = 25 + 273.15  # [K]
P_i = 30 # bar
P_f = 350 # bar

eff_compr = 0.75

k = 1.43 # from CoolProp

n_stages = 3 
beta = (P_f/P_i)**(1/n_stages)  #compression ration in each stage

l_ad_ms = n_stages * k/(k-1) * R_specific * T_1 * ( (beta)**((k-1)/k) - 1 )      # [J/kg]
l_real_ms = l_ad_ms/eff_compr    #[J/kg]
l_compr_ms = l_real_ms / 3600 / 1000 # [kWh/kg]

###########################################################################################################################################
'output lists'
EL_cell_output = []
EL_P_output = []
EL_H2_prod_output = []
EL_H2_prod_output_y = []
EL_CF_output = []

C_H2_prod_output = [] # High Pressure Hydrogen

FC_cell_output = []
FC_P_output = []
FC_H2_prod_output = []
FC_CF_output = []

pv_output = []

BESS_capacity_output = []
BESS_SOH_output = []

HP_tank_output = []
LP_tank_output = []

E_RES_output = []
E_comp_output = [] # Energy required by the compressor
E_grid_list = []
E_to_H2_output = []

#excess and deficit with initial RES
E_excess_RES_output = []
E_deficit_RES_output = []
RES_self_consumption = []

#excess and deficit after the BESS
E_excess_BESS_output = []
E_deficit_BESS_output = []
BESS_self_consumption = []

#excess and deficit after H2
E_excess_H2_output = []
E_deficit_H2_output = []
H2_self_consumption = []



#%%

###########################################################################################################################################
'MAIN'

def complete_sim(df_data, s):
    
    #datasets creation
    P_wind = df_data['wind_power']
    P_pv = df_data['PV_power']
    P_load = df_data['load']
    T_ext = df_data['temperature']

    date = df_data['date']
     
    kWh_factor = 60   #dati min

    EL_size = s[0]
    FC_size = s[1]
    BESS_size = s[2]
    Tank_size = s[3]
    PV_upgrade = s[4]
    
    if EL_size == 0 or FC_size == 0:
        H2_storage = False
    else: 
        H2_storage = True
    
    'power fluxes'
    #available power form RES     
    P_RES = P_wind + P_pv * ( 1 + PV_upgrade / 16)
    #the goal is to cover the island demand
    P_goal_list = P_load
    
    'ELECTROLYZER'
    EL_cell_power = 9.45         #kW
    #number of availabe cells
    EL_cell_number = EL_size
    #electrolyzer stack nominal pwoer [kW]
    EL_P_nom = EL_cell_number * EL_cell_power 
    #power required by the alkaline electrolyzer to start the hydrogen production
    EL_P_min = 0.2 * EL_P_nom
    #new electrolyzer condition
    EL_h_work = 0
    # intial electrolyzer temperature
    EL_T_0 = 71
    EL_T_list = [EL_T_0]
    stand_by = 0
    #initial conversion factor
    EL_CF_list = [0.018]
    #conversion factor
    EL_CF = 0.018 # kg/kWh  hydrogen mass that the electrolyzer can produce with 1kWh
    #list to save CF while EL is active
    EL_CF_active_list = []

    
    'FUEL CELL'
    FC_cell_power = 13.57         #kW
    #number of availabe cells
    FC_cell_number = FC_size
    #electrolyzer stack nominal pwoer [kW]
    FC_P_nom = FC_cell_number * FC_cell_power
    #power required by the alkaline electrolyzer to start the hydrogen production
    FC_P_min = 0.01 * FC_P_nom
    #new electrolyzer condition
    FC_h_work = 0
    # intial electrolyzer temperature
    FC_T_0 = 60
    FC_T_list = [FC_T_0]
    stand_by = 0
    #initial conversion factor
    FC_CF_list = [0.059]
    #conversion factor
    FC_CF = 0.059 # kg/kWh  hydrogen mass that the fuel cell requires to produce 1kWh
    #list to save CF while FC is active
    FC_CF_active_list = []
    
    'BESS'
    #battery capacity [kWh]
    BESS_capacity = BESS_size
    #new bess condition
    BESS_degr = 0 
    BESS_SOH_list= [1] 
    # initial SOC hypotesis
    BESS_SOC_list = [0.4] 
    BESS_SOC_day    = [0] 
    BESS_C_rate_day = [0]
    #charge and discharge C-rate 
    BESS_C_rate_C_list = []
    BESS_C_rate_D_list = []
    
    'TANK - high pressure (350 bar)'  
    #high pressure tank capacity [kg]
    tank = Tank_size
    H2_buffer_list = [0.1*tank]
    if tank == 0:
        H2_buffer_list = [0]
    H2_buffer = H2_buffer_list[0]
    full_tank = False
    grid_support = False
    
    'TANK - low pressure (30 bar)'  
    #low pressure tank capacity [kg]
    lp_tank = 10
    H2_lp_buffer_list = [0]
    H2_lp_buffer = H2_lp_buffer_list[0]
    counter = 0
    
    # time_to_compress = 30 #np.ceil(30 * s[4]/20)  # [min]
    time_to_compress = lp_tank / (60/kWh_factor)   # [min] 1kg/min compression
    # times_output.append(s[6])
    
    'H2 request'
    H2_cum  = 0
    EL_H2_prod = [0]
    
    #lists to track the variation of quantities in time
    EL_P_recieved_list = []
    EL_H2_prod_list = []
    EL_H2_prod_list_y = []
    EL_H2_prod_y = []
    
    C_H2_prod_list = []
    C_P_list = []
    
    FC_P_delivered_list = []
    FC_H2_req_list = []
    
    P_BESS_list = []
    
    P_BESS_excess_list  = []
    P_BESS_deficit_list  = []
    P_excess_list  = []
    P_deficit_list  = []
    
    P_comp_list = []    
    'for loop for each timestep of the timeframe'
    for i in range(len(P_RES)):
        
        P_compressor = l_compr_ms*(lp_tank/time_to_compress)*kWh_factor 
        #########################################################
        'target power'
        #if the battery supports the load
        if counter != 0: # If the counter is not equal to 0, the compressor will work so extra load
            P_requested = P_load[i] + P_compressor
        
        else: # If the counter is 0, the low pressure tank is not full yet so the compressor is off
            P_requested = P_load[i]
            
        #########################################################
        'battery operation'
        P_BESS, BESS_SOC, BESS_SOH, BESS_degr, C_rate_C, C_rate_D = battery_operation(i,P_RES[i],P_requested, Capacity=BESS_capacity,
                                                                          SOC_old=BESS_SOC_list[i],SOH_old=BESS_SOH_list[i],Degr=BESS_degr,
                                                                          SOC_day=BESS_SOC_day,C_rate_day = BESS_C_rate_day, 
                                                                          kWh_factor=kWh_factor) 
        
        #BESS parameters tracking
        BESS_SOC_list.append(BESS_SOC)
        BESS_SOC_day.append(BESS_SOC)
        BESS_SOH_list.append(BESS_SOH)
        
        BESS_C_rate_C_list.append(C_rate_C)
        BESS_C_rate_D_list.append(C_rate_D)
        BESS_C_rate_day.append(C_rate_C + C_rate_D)
        
        if (i+1) % kWh_factor*24 == 0:
            BESS_SOC_day    = [ ]                  #new day - new SOC profile for degradation assessment 
            BESS_C_rate_day = [ ]
        
        #power coming from RES + BESS
        P_BESS_list.append(P_BESS)
        
        #########################################################
        'residualP_RESmismatch'

        if P_BESS > P_requested:
            P_BESS_excess = P_BESS - P_requested
            P_BESS_deficit = 0
            
            if counter != 0:
                H2_to_c = lp_tank/time_to_compress #H2 to be compressed min 
                counter = counter - 1 # The compressor will work until the counter is back at 0. 
                H2_lp_buffer = H2_lp_buffer - lp_tank/time_to_compress # Amount of h2 left in low pressure tank
            
            else:
                H2_to_c = 0
                P_compressor = 0
                
        else: 
            P_BESS_excess = 0
            P_BESS_deficit = P_requested - P_BESS
            H2_to_c = 0
            P_compressor = 0
            
        P_comp_list.append(P_compressor)

        P_BESS_excess_list.append(P_BESS_excess)
        P_BESS_deficit_list.append(P_BESS_deficit)   
        
        
        if H2_storage == True: 
            
            #########################################################
            'eletrolyzer activation'
            #conversion factor update
            EL_CF,EL_f_i_V,EL_f_H2_i,_ = EL_model(EL_T_list[i], EL_h_work, EL_cell_number, kWh_factor)
            #trend of the conversion factor
            EL_CF_list.append(EL_CF)
            
            #H2 production calculation in the given minute
            if P_BESS_excess > EL_P_min:
                if P_BESS_excess < EL_P_nom:
                    EL_P_given = P_BESS_excess
                else:
                    EL_P_given = EL_P_nom
                
                EL_H2_prod = EL_P_given * EL_CF / kWh_factor
                
                #produce only the hydrogen mass that fits in the lp_tank
                if EL_H2_prod + H2_lp_buffer > lp_tank:
                    EL_H2_prod = lp_tank - H2_lp_buffer
                    EL_P_given = EL_H2_prod / EL_CF * kWh_factor
                    # counter = time_to_compress # compressor starts working for the given amount of time when tank is full.

                if H2_to_c + H2_buffer > tank:
                    H2_to_c = (tank - H2_buffer) if (tank - H2_buffer) > 0 else 0
                    EL_H2_prod = 0
                    EL_P_given = 0
                
                EL_CF_active_list.append(EL_CF)
                
            else:
                EL_H2_prod = 0
                EL_P_given = 0
                
                
            #trend of the power fed to the electrolyzer
            EL_P_recieved_list.append(EL_P_given)
            #H2 produced at each timestep
            EL_H2_prod_list.append(EL_H2_prod)
            #annual hydrogen yield
            EL_H2_prod_list_y.append(EL_H2_prod)  
            
            #H2 produced at each timestep during compression
            C_H2_prod_list.append(H2_to_c)
            C_P_list.append(P_compressor)
            
            
            'Thermal management'
            EL_T = EL_transit(EL_H2_prod, EL_f_i_V, EL_f_H2_i, EL_T_list[i], EL_cell_number, T_ext[i], kWh_factor) 
            EL_T_list.append(EL_T)    #electrolyzer temperature evolution in time
            
            #working hours counting only if activated
            if EL_H2_prod > 0:
                EL_h_work = EL_h_work + 1/kWh_factor
            
            #########################################################
            'Excess power from RES, not converted to H2'
            P_excess_list.append(P_BESS_excess - EL_P_given)        
            ########################################################
    
            
            #########################################################
            'fuel cell activation'
            
            FC_CF,FC_f_i_V,FC_f_H2_i = FC_model(FC_T_list[i], FC_h_work, FC_cell_number, kWh_factor)
            # trend of the fuel cell conversion factor
            FC_CF_list.append(FC_CF)
            
            # H2 consumption calculation in the given minute
            if P_BESS_deficit > FC_P_min:
                    
                if P_BESS_deficit < FC_P_nom:
                    FC_P_delivered = P_BESS_deficit
                else:
                    FC_P_delivered = FC_P_nom
                
                FC_H2_req = FC_P_delivered * FC_CF / kWh_factor
                
                #conversion in electricity of the residual hydrogen in the tank
                if (H2_buffer + H2_lp_buffer) < FC_H2_req:
                    FC_H2_req = H2_buffer + H2_lp_buffer
                    FC_P_delivered = (H2_buffer + H2_lp_buffer) / FC_CF * kWh_factor
                
                FC_CF_active_list.append(FC_CF)
                
            else:
                FC_H2_req = 0
                FC_P_delivered = 0
    
            #trend of the power delivered by the fuel cell
            FC_P_delivered_list.append(FC_P_delivered)
            #H2 consumed at each timestep
            FC_H2_req_list.append(FC_H2_req)
            
            'Thermal management'
            FC_T = FC_transit(FC_H2_req, FC_f_i_V, FC_f_H2_i, FC_T_list[i], FC_cell_number, T_ext[i], kWh_factor) 
            FC_T_list.append(FC_T)    #FC stack temperature evolution in time
            
            #working hours counting only if activated
            if FC_H2_req > 0:
                FC_h_work = FC_h_work + 1/kWh_factor
            
            #########################################################
            'Deficit power, not covered by H2'
            P_deficit_list.append(P_BESS_deficit - FC_P_delivered)
            #########################################################
            'tank management'
            H2_lp_buffer = H2_lp_buffer + EL_H2_prod
            
            if H2_lp_buffer/lp_tank > 0.9:
                counter = time_to_compress # compressor starts working for the given amount of time when tank is full.

            
            H2_buffer = H2_buffer + H2_to_c
            
            if H2_lp_buffer > FC_H2_req:
                H2_lp_buffer = H2_lp_buffer - FC_H2_req
            
            else:
                H2_buffer = H2_buffer - (FC_H2_req - H2_lp_buffer)
                H2_lp_buffer = 0
            
            H2_lp_buffer_list.append(H2_lp_buffer)
            H2_buffer_list.append(H2_buffer)
            
            counterlist.append(counter)
            
            #final confersion factors to estimate time degradation
            EL_CF_final,_,_,_ = EL_model(71, EL_h_work, EL_cell_number, kWh_factor)
            FC_CF_final,_,_ = FC_model(60, FC_h_work, FC_cell_number, kWh_factor)
        
        else:
            P_excess_list.append(P_BESS_excess)  
            P_deficit_list.append(P_BESS_deficit)
            
            EL_CF_final = 0
            FC_CF_final = 0
        
    'Data saving after the for loop'        
    E_RES = (sum(P_RES)/kWh_factor)/1000                                #[MWh]  available energy from RES after BESS
    E_load = (sum(P_load)/kWh_factor)/1000                              #[MWh]  total energy required by load
    
    #excess and deficit Energy RES
    P_mismatch = P_RES - P_load                                             #[kW] power mismatch between RES and load
    E_deficit_RES = - sum(p for p in P_mismatch if p < 0)/kWh_factor/1000   #[MWh]  deficit energy with initial RES
    E_excess_RES = sum(p for p in P_mismatch if p > 0)/kWh_factor/1000      #[MWh]  excess energy with initial RES
    E_to_load_RES = E_load - E_deficit_RES                                  #[MWh]  energy feeding the load with initial RES
    
    #excess and deficit with BESS
    E_deficit_BESS = (sum(P_BESS_deficit_list)/kWh_factor)/1000          #[MWh]  deficit energy after BESS storage
    E_excess_BESS = (sum(P_BESS_excess_list)/kWh_factor)/1000            #[MWh]  excess energy after BESS storage
    E_to_load_BESS = E_load - E_deficit_BESS                             #[MWh]  energy feeding the load after BESS

    E_comp = (sum(C_P_list)/kWh_factor)/1000                             #[MWh]  electrical en absorbed by compressor
    E_RES_to_H2 = (sum(EL_P_recieved_list)/kWh_factor)/1000              #[MWh]  electrical en converted to hydrogen

    #excess and deficit with H2
    E_deficit_H2 = (sum(P_deficit_list)/kWh_factor)/1000                 #[MWh]  deficit energy after H2 storage
    E_excess_H2 = (sum(P_excess_list)/kWh_factor)/1000                   #[MWh]  excess energy after H2 storage
    E_to_load_H2 = E_load - E_deficit_H2                                 #[MWh]  energy feeding the load after H2
    
    'outputs'
    #BESS capacity   [MWh]
    BESS_capacity_output = BESS_capacity         
    #SOH at the end of the year
    BESS_SOH_output = BESS_SOH_list[-1]
    #number of EL cells
    EL_cell_output = EL_cell_number
    #number of FC cells
    FC_cell_output = FC_cell_number
    #PV scale
    pv_output = 160 * (1 + PV_upgrade/16)
    #dimension of tanks 
    HP_tank_output = tank
    LP_tank_output = lp_tank
    
    #Hydrogen production by EL
    EL_H2_prod_output = sum(EL_H2_prod_list)
    #Hydrogen after compression
    C_H2_prod_output = sum(C_H2_prod_list)
    
    
    #average EL conversion factor
    # EL_CF_output = sum(EL_CF_list)/len(EL_CF_list)*1000
    if len(EL_CF_active_list) != 0:
        EL_CF_output = sum(EL_CF_active_list)/len(EL_CF_active_list)*1000
    else:
        EL_CF_output = EL_CF_list[0]

    #average EL conversion factor
    # FC_CF_output = sum(FC_CF_list)/len(FC_CF_list)*1000
    if len(FC_CF_active_list) != 0:
        FC_CF_output = sum(FC_CF_active_list)/len(FC_CF_active_list)*1000
    else:
        FC_CF_output = FC_CF_list[0]


    #available energy from renewables
    E_RES_output = E_RES
    #unsatisfied load request by RES
    E_deficit_RES_output = E_deficit_RES
    #wasted energy by RES
    E_excess_RES_output = E_excess_RES
    
    #unsatisfied load request by RES
    E_deficit_BESS_output = E_deficit_BESS
    #wasted energy by RES
    E_excess_BESS_output = E_excess_BESS   
    
    #Energy absorbed by compression
    E_comp_output = E_comp
    #energy converted to hydrogen
    E_to_H2_output = E_RES_to_H2
    
    #unsatisfied load request
    E_deficit_H2_output = E_deficit_H2
    #wasted energy
    E_excess_H2_output = E_excess_H2   
    
    #self consumption RES
    RES_self_consumption = E_to_load_RES/E_load * 100
    #self consumption BESS
    BESS_self_consumption = E_to_load_BESS/E_load * 100
    #self consumption H2
    H2_self_consumption = E_to_load_H2/E_load * 100
    

    
    'output'
    output = pd.DataFrame()
    output['BESS[MWh]'] = [BESS_capacity_output]
    output['SOH_final'] = [BESS_SOH_output]

    output['PV_power[kWp]'] = [pv_output]
    output['EL_n_cells'] = [EL_cell_output]
    output['FC_n_cells'] = [FC_cell_output]
    output['HP_tank[kg]'] = [HP_tank_output]
    output['LP_tank[kg]'] = [LP_tank_output]

    output['EL_CF[kg/MWh]'] = [EL_CF_output]
    output['FC_CF[kg/MWh]'] = [FC_CF_output]
    
    output['EL_CF_fin'] = [EL_CF_final]
    output['FC_CF_fin'] = [FC_CF_final]
    output['EL_h_work'] = [EL_h_work]
    output['FC_h_work'] = [FC_h_work]

    output['H2_prod_EL[kg]'] = [EL_H2_prod_output]
    output['H2_Comp [kg]']  = [C_H2_prod_output]

    output['E_RES[MWh]']= [E_RES_output]
    output['E_deficit_RES[MWh]']= [E_deficit_RES_output]
    output['E_excess_RES[MWh]']= [E_excess_RES_output]
    output['RES_SC[%]'] = [RES_self_consumption]

    output['E_BESS_deficit[MWh]']= [E_deficit_BESS_output]
    output['E_BESS_excess[MWh]'] = [E_excess_BESS_output]
    output['BESS_SC[%]'] = [BESS_self_consumption]

    output['E_to_H2[MWh]'] = [E_to_H2_output]
    output['E_comp[MWh]'] = [E_comp_output]

    output['E_H2_deficit[MWh]']= [E_deficit_H2_output]
    output['E_H2_excess[MWh]'] = [E_excess_H2_output]
    output['H2_SC[%]'] = [H2_self_consumption]
    
    return(output)


