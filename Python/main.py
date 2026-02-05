
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

import time

from LCORE_calculator import LCORE_function
from complete_simulation import complete_sim
from extra_simplified_simulation import extra_simplified_sim
from scipy.optimize import curve_fit

start_time = time.time()

year = 2020

"""
USER INPUT REQUIRED: dataframe containing power production and load

"""


with open('df_load_and_power.pkl','rb') as f:
    df_data = pickle.load(f) 
    kWh_factor = 60   #minute data

#%%
'definition of maximum sizes and simulation resolution for each component'
comp_dict = {}

comp_dict['EL']   = {'max_s': 70,    # EL   (max n cells (9.45 kW) = - kW)
                     'res': 5      } # EL   (5 cells)
                                        
comp_dict['FC']   = {'max_s': 90,    # FC   (max n cells (13 kW) = - kW)
                     'res': 5      } # FC   (5 cells)

comp_dict['Tank']  = {'max_s': 10000,      # Tank (max 10 000 h2 kg)
                      'res': 100        }  # Tank (100 h2 kg)

comp_dict['BESS']  = {'max_s': 25000,     # BESS (max 25 000 kWh)
                      'res': 50        }  # BESS (50 kWh modules)

comp_dict['PV']   = {'max_s': 200,      # PV   (max + 200 x 10 kWp arrays = 2160 kWp)
                     'res': 5        }  # PV (extra 10 kWp arrays)

#%%
'definition of economic parameters'

prices = pd.read_excel('prices_excel.xlsx', sheet_name = ['Li-BESS', 'ALK EL', 'PEM FC', 'H2 Tank', 'PV', 'Onshore WT'],
                       usecols = 'V:Y', skiprows= [0,1], nrows = 3 )


if year == 2020:
    k = 0
elif year == 2030:
    k = 1
elif year == 2050:
    k = 2

EL_cost      = prices['ALK EL']['avg'][k]           # €/kW
FC_cost      = prices['PEM FC']['avg'][k]           # €/kW     
HP_tank_cost = prices['H2 Tank']['avg'][k]           # €/kg_h2
LP_tank_cost = prices['H2 Tank']['avg'][k]           # €/kg_h2
bess_cost    = prices['Li-BESS']['avg'][k]           # €/MWh
WT_cost      = prices['Onshore WT']['avg'][k]          # €/kW
PV_cost      = prices['PV']['avg'][k]           # €/kWp

comp_cost = 60000    #€/unit

components = {}

EN_cost      = 165000 #  #€/MWh    cost of electricity

components['EL'] = {'total installation costs': EL_cost,        # €/
                    'OeM': 0.0275*EL_cost,                      # €/kW/y
                    'lifetime': 10, 'relpacement': 0.4}

components['FC'] = {'total installation costs': FC_cost,           # €/kW - ref. file 'Costi.xls' 460 €/kg
                    'OeM': 0.0275*FC_cost,                          # €/kW/h
                    'lifetime': 10, 'relpacement': 0.4}

components['BESS'] = {'total installation costs': bess_cost,       # €/MWh
                      'OeM': 0.025*bess_cost,                      # €/MWh/y
                      'lifetime': 10, 'relpacement': 0.8}

components['HP_tank'] = {'total installation costs': HP_tank_cost,      # €/kg
                        'OeM': 0.01*HP_tank_cost,                       # €/kg/y
                        'lifetime': 25, 'relpacement': 0}

components['LP_tank'] = {'total installation costs': LP_tank_cost,      # €/kg
                        'OeM': 0.01*LP_tank_cost,                       # €/kg/y
                        'lifetime': 25, 'relpacement': 0}

components['WT'] = {'total installation costs': WT_cost,           # €/kW - ref. file 'Costi.xls' 460 €/kg
                     'OeM': 0.025*WT_cost,                                    # €/kW/h
                     'lifetime': 25, 'relpacement': 0}

components['PV'] = {'total installation costs': PV_cost,           # €/kW - ref. file 'Costi.xls' 460 €/kg
                    'OeM': 0.025*PV_cost,                          # €/kW/h
                    'lifetime': 25, 'relpacement': 0}

components['compressor'] = {'total installation costs': comp_cost,           # €/kW - ref. file 'Costi.xls' 460 €/kg
                            'OeM': 0.025*comp_cost,                                    # €/kW/h
                            'lifetime': 25, 'relpacement': 0, 'size' : 1}

lifetime = 20       #time horizon of the economic analysis (1 stack substitution, 1 bess substitution, no substitution of RES)
r = 0.05     #interest rate

'energy vectors dictionaries'
electricity = {'purchase price from grid': EN_cost, 'sale price to grid': 0}   # electricity dictionary
hydrogen = {'sale price': 0}     # hydrogen dictionary


#%%

def LCORE_minimizer(s):
    
# s_list = [[30, 60, 1000, 2788, 40]]
# for s in s_list:
    
    # print('config: ' + str(s), flush = True)

    s[0] = s[0] * comp_dict['EL']['res']
    s[1] = s[1] * comp_dict['FC']['res']
    s[2] = s[2] * comp_dict['BESS']['res']
    s[3] = s[3] * comp_dict['Tank']['res']
    s[4] = s[4] * comp_dict['PV']['res']
            
    'complete sumulation of the first year to assess the degradation of components and actual performance indexes'
    complete_output = complete_sim(df_data, s)
    
    'components size definition'
    sizes = {}
    sizes['EL']      =   complete_output['EL_n_cells'][0] * 9.45         # kW
    sizes['FC']      =   complete_output['FC_n_cells'][0] * 13.57        # kW
    sizes['BESS']    =   complete_output['BESS[MWh]'][0]         # MWh 
    sizes['HP_tank'] =   complete_output['HP_tank[kg]'][0]                # kg
    sizes['LP_tank'] =   complete_output['LP_tank[kg]'][0]                # kg
    sizes['PV']      =   complete_output['PV_power[kWp]'][0]                # kWp
    sizes['WT']      =   800                           # kW
    
    # if sizes['EL'] == 0 or sizes['FC'] == 0:
    if complete_output['EL_h_work'][0] == 0 or complete_output['FC_h_work'][0] == 0:
        sizes['compressor'] = 0
        
    else:
        sizes['compressor'] = 1
    
    'components lifetime calculation'
    lifetimes = {}
    

    'future degradated parameters' 
    ##############################################################
    'BESS Exp capcity fade'
    SOHy = complete_output['SOH_final'][0]
    
    m = -5.43e-07
    q =  0.00763

    corr = m * complete_output['BESS[MWh]'][0] + q
    if corr < 0:
        corr = 0
    
    y_data = [1, (1+SOHy)/2 + corr, SOHy]
    x_data = [0,0.5,1]
    
    def fit_func(x, a):
          return a * x**(1.06) + 1
    
    params = curve_fit(fit_func, x_data, y_data)
    [a] = params[0]
    
    x_fit = np.arange(0,10)
    y_fit = [a * (x) ** 1.06 + 1 for x in x_fit ]
    
    SOH_list = []
    for y in y_fit:
        if y > 0.7:
            SOH_list.append(y)
            
    x_fit2 = np.arange(0,11)
    y_fit2 = [a * (x) ** 1.06 + 1 for x in x_fit2 ]
            
    SOH_list_avg = []
    for i in range(len(y_fit2)-1):
        if y_fit2[i] > 0.7:
            SOH_list_avg.append((y_fit2[i]+y_fit2[i+1])/2)
            
    lifetimes['BESS'] = len(SOH_list)
    
    SOH_list20 = SOH_list * int(np.ceil(( 20 / lifetimes['BESS'] )))
    SOH_list20 = SOH_list20[:21]
    
    SOH_list20_avg = SOH_list_avg * int(np.ceil(( 20 / lifetimes['BESS'] )))
    SOH_list20_avg = SOH_list20_avg[:21]
    
    Capacity_list = [item * sizes['BESS'] for item in SOH_list20_avg]

    
    ##############################################################
    'EL capacity factor fade'
    if complete_output['EL_h_work'][0] == 0 or complete_output['FC_h_work'][0] == 0:
        lifetimes['EL'] = 10
        EL_CF_list = [18 / 1000] * 20
        lifetimes['FC'] = 10
        FC_CF_list = [59 / 1000] * 20
        
    else: 
        EL_V_max = 2.3  #V
        EL_I_id = 5000  #A
        EL_H2_nom = 18 / 106  #kg/h - 106 cells in the 1MW stack/module
        EL_CF_lim = EL_H2_nom / (EL_V_max * EL_I_id / 1000000)  # kg/MWh
        
        #final EL CF trend
        def fit_line(x, m, q):
            return m * x + q
        
        x_el = [-1,0]
        y_el = [18,complete_output['EL_CF_fin'][0] * 1000]
        
        line_params = curve_fit(fit_line, x_el, y_el)
        [m,q] = line_params[0]
        
        x_fit = np.arange(0,10)
        y_fit_el = [m * x + q for x in x_fit]
        
        EL_CF_fin_list = []
        for y in y_fit_el:
            if y > EL_CF_lim:
                EL_CF_fin_list.append(y)
            
    
        lifetimes['EL'] = len(EL_CF_fin_list)
        EL_CF_fin_list20 = EL_CF_fin_list * int(np.ceil(( 20 / lifetimes['EL'] )))
        EL_CF_fin_list20 = EL_CF_fin_list20[:21]
    
        #Delta CF function of BESS SOH trend
        m0 = 1.1
        x_p = complete_output['SOH_final'][0]
        y_p = complete_output['EL_CF_fin'][0] * 1000 - complete_output['EL_CF[kg/MWh]'][0]
        
        DFC_EL_list = [m0 * (x - x_p) + y_p for x in SOH_list20]
        
        #Average CF trend
        EL_CF_list = []
        for i in range(len(EL_CF_fin_list20)):
            EL_CF_list.append(EL_CF_fin_list20[i] - DFC_EL_list[i])
    
        ##############################################################
    
        FC_V_min = 46.2  #V
        FC_I_id = 230  #A
        FC_H2_nom = 59 / 74  #kg/h - 74 stacks in the 1MW module
        FC_CF_lim = FC_H2_nom / (FC_V_min * FC_I_id / 1000)
        
        bess_size = complete_output['BESS[MWh]'][0]
        
        c = complete_output['FC_CF[kg/MWh]'][0] 
        b = 1.25
        
        k1 = 700.23
        k2 = -0.386
        
        a = k1 * np.exp(bess_size /1000 * k2) / 1000
        
        x_fit = np.arange(0,10)
        y_fit_fc = [ a * (x) ** b + c for x in x_fit ]
        
        FC_CF_list1 = []
        for y in y_fit_fc:
            if y > FC_CF_lim:
                FC_CF_list1.append(y)
        
        if complete_output['FC_h_work'][0] != 0:
            lifetimes['FC'] = len(FC_CF_list1)
        else: 
            lifetimes['FC'] = 10
        
        FC_CF_list = FC_CF_list1 * int(np.ceil(( 20 / lifetimes['FC'] )))
        FC_CF_list = FC_CF_list[:21]
    
    
    ##############################################################
    
    
    'simplified simulation of fugure years with degradated components'
    
    df_output_years = complete_output.copy()
    
    df_output_years = df_output_years.drop(['EL_CF_fin','FC_CF_fin','EL_h_work','FC_h_work'], axis = 1)
    
    for i in range(1,20):
        simp_output_i = extra_simplified_sim(df_data, s, Capacity_list[i], EL_CF_list[i]/1000, FC_CF_list[i]/1000)
        
        df_output_years = pd.concat([df_output_years, simp_output_i], axis = 0).reset_index(drop=True)        
            
    
    'LCORE'    
    LCORE = LCORE_function(sizes, df_output_years['E_H2_deficit[MWh]'], components, electricity , lifetime, hydrogen, r)

    # print('config: ' + str(s) + '\nLCORE: ' +  str(LCORE), flush = True)

    return LCORE #, output

    

#%%
from scipy.optimize import differential_evolution

def LCORE_min_wrapper(s):
    
    try:
        LCORE = LCORE_minimizer(s)
        print('config: ' + str(s) + '\nLCORE: ' +  str(LCORE), flush = True)
        # print(LCORE, flush = True)
        return LCORE
        
    except:
        print('config: ' + str(s) + 'error in this iteration')
        # print('error in this iteration')
        return np.inf

bounds = [(0, comp_dict['EL']['max_s']   / comp_dict['EL']['res']),          
          (0, comp_dict['FC']['max_s']   / comp_dict['FC']['res']),            
          (1, comp_dict['BESS']['max_s'] / comp_dict['BESS']['res']),         
          (0, comp_dict['Tank']['max_s'] / comp_dict['Tank']['res']),        
          (0, comp_dict['PV']['max_s']   / comp_dict['PV']['res'])            
          ]

# LCORE, output = LCORE_minimizer([10, 10, 20000, 100, 13])

if __name__ == "__main__":
    
    result = differential_evolution(LCORE_min_wrapper,          #LCORE_minimizer
                                    bounds, 
                                    #tol=0.001, 
                                    integrality = [True, True, True, True, True], 
                                    updating = 'deferred', 
                                    workers = -1)
    
    end_time = time.time()
    print("--- %s seconds ---" % (end_time - start_time))
    

#%%
    'Output'

    df_output = pd.DataFrame()
    df_output['EL']   = [result.x[0] * comp_dict['EL']['res']]
    df_output['FC']   = [result.x[1] * comp_dict['FC']['res']]
    df_output['BESS'] = [result.x[2] * comp_dict['BESS']['res']]
    df_output['Tank'] = [result.x[3] * comp_dict['Tank']['res']]
    df_output['PV']   = [160 * (1 + result.x[4] * comp_dict['PV']['res'] / 16)]
    df_output['LCORE'] = [result.fun]
    df_output['time'] = [end_time - start_time]

    df_output.to_csv('output' + str(year) + '.csv', sep = ';')























