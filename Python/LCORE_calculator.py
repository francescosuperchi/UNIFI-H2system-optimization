"""
Citation notice:

If you use this model, please cite:
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645

"""

import pandas as pd
import numpy as np 


'''
levelized cost of requested energy (LCORE)

- modified version of LCOE where the energy considered is only what the load requires, excess energy is not considered

'''

def LCORE_function(sizes, E_def_list,  components, electricity , lifetime, hydrogen, r):
    
    components['EL']['size']         =   sizes['EL']    # kW
    components['FC']['size']         =   sizes['FC']    # kW
    components['BESS']['size']       =   sizes['BESS']             # MWh 
    components['HP_tank']['size']    =   sizes['HP_tank']           # kg
    components['LP_tank']['size']    =   sizes['LP_tank']            # kg
    components['PV']['size']         =   sizes['PV']         # kWp
    components['WT']['size']         =   sizes['WT']                             # kWp
    components['compressor']['size'] =   sizes['compressor']                             # kWp
    
    'hydrogen production'
    hydrogen['produced [kg/y]'] = 0                # Annual volumetric hydrogen output [kg/y]

    'electricity request/production'
    electricity['excess'] = 10
    electricity['sold'] = 10
    electricity['saved'] = 3007.74  # - H2_en_def       #MWh saved energy 
    
    N = lifetime + 1
    OeM_y = 0
    I0 = 0
    C_subs = 0
    
    for tech in components:
        #total investment cost
        I0 = I0 + components[tech]['size'] * components[tech]['total installation costs']
        #total annual cost for Operation and Maintenance
        OeM_y = OeM_y + components[tech]['size'] * components[tech]['OeM']
        
    CAPEX_list   = []
    OeM_list     = []
    EN_list = []
    EN_y = electricity['saved'] 
    
    for n in range(N):
        if n == 0:
            CAPEX_list.append(I0)
            OeM_list.append(0)
            EN_list.append(0)
            
        else:
            CAPEX_list.append(0)
            OeM_list.append( (OeM_y + E_def_list[n-1]  * electricity['purchase price from grid'] ) / ((1+r)**n) )
            
            EN_list.append( (EN_y) / ((1+r)**n) )
        
    for tech in components:
        subs_years = np.arange(0,20,components[tech]['lifetime']).tolist()
        subs_years = subs_years[1:]
        
        for n in range(N):
            if n in subs_years and n != 20:
                C_subs = components[tech]['size'] * components[tech]['total installation costs'] * components[tech]['relpacement']
                CAPEX_list[n] = CAPEX_list[n] + (C_subs / ((1+r)**n) ) 
    
    dfLCORE = pd.DataFrame()
    
    dfLCORE['CAPEX'] = CAPEX_list
    dfLCORE['OeM'] = OeM_list
    dfLCORE['NUM'] = dfLCORE['CAPEX'] + dfLCORE['OeM']
    dfLCORE['EN'] = EN_list
    LCORE = sum(dfLCORE['NUM']) / sum(dfLCORE['EN'])
    
    if LCORE == None:
        LCORE = 0
    
    # print(LCORE)
    return LCORE











