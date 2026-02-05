"""
Citation notice:

If you use this model, please cite:
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645

"""

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

print(l_compr_ms)

