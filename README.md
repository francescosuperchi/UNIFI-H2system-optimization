# UNIFI-H2system-optimization
Main repository for a degradation-aware optimization framework for hybrid energy systems comprising renewables, batteries and hydrogen storage developed in Python by the University of Florence (Italy)


Open-source implementation that replicates the simulation and stochastic optimization workflow presented in:

> F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, *Applied Energy*, vol. 377, Part D, p. 124645, 2025.  
> **On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage**  
> https://doi.org/10.1016/j.apenergy.2024.124645

This repository focuses on techno-economic sizing and long-term assessment of a hybrid energy system including:
- Renewable generation: photovoltaic power and wind power
- Short-term storage: Lithium-ion battery (BESS)
- Seasonal storage: hydrogen chain (electrolyzer, compressor, tank(s), fuel cell)
- Degradation-aware simulation coupled with stochastic optimization to minimize the long-term cost of energy supply

The implemented approach captures component degradation effects while avoiding the computational burden of fully physics-based multi-year simulations, achieving large runtime reductions while preserving accuracy in long-term performance indicators.

<img width="4514" height="1126" alt="hybrid sim wide" src="https://github.com/user-attachments/assets/ac1d2b86-25ad-477e-bff6-2b37849eee9d" />


---

## Citation

If this model is used in academic or technical work, please cite:

```text
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645
```

---

## Overview of the methodology

### Degradation-aware two-stage simulation

The workflow is based on a two-stage strategy:

1. **Complete first-year simulation**  
   A detailed physics-based simulation is executed for the first year to:
   - evaluate operational performance,
   - quantify component usage and stress,
   - estimate degradation endpoints (for example battery SOH, electrolyzer and fuel cell performance decay).

2. **Extra-simplified multi-year simulation**  
   The remaining project lifetime is simulated using a reduced-order model where degraded parameters are injected year by year:
   - effective battery capacity derived from SOH evolution,
   - electrolyzer and fuel cell capacity factor trends,
   - component replacement logic based on estimated lifetimes.

This approach allows robust estimation of long-term energy deficits and costs at a fraction of the computational cost of full multi-year detailed simulations.

### Economic assessment and optimization

For each candidate system configuration:
- life-cycle costs are computed including CAPEX, O&M, and replacements,
- discounted cash-flow analysis is performed,
- the Levelized Cost of Required Energy (LCORE) is used as the objective function.

System sizing is solved using a stochastic optimization based on differential evolution with discrete decision variables.

---

## Repository structure

The main script relies on the following modules:

- `complete_simulation.py`  
  Detailed first-year simulation used to extract degradation indicators and operational KPIs.

- `extra_simplified_simulation.py`  
  Fast reduced-order simulation for subsequent years using degraded parameters.

- `LCOS_calculator.py`  
  Implementation of the `LCOS_function(...)` used as objective function.

### Required input files

- `df_load_and_power.pkl`  
  Pickled pandas DataFrame containing load demand and renewable power production time series.

- `prices_excel.xlsx`  
  Excel file containing component cost data. Expected sheets:
  - `Li-BESS`
  - `ALK EL`
  - `PEM FC`
  - `H2 Tank`
  - `PV`
  - `Onshore WT`

### Output files

- `output<year>.csv`  
  CSV file containing the optimal system sizing, LCOS value, and runtime for the selected scenario year.

---

## Inputs

### Time series data

The file `df_load_and_power.pkl` must contain the load and renewable production signals required by `complete_simulation(...)` and `extra_simplified_simulation(...)`. The time resolution is defined through the `kWh_factor` parameter in the main script.

Ensure that column names and units are consistent with the expectations of the simulation modules.

### Economic data

The file `prices_excel.xlsx` is read as:

```python
pd.read_excel(
    'prices_excel.xlsx',
    sheet_name=['Li-BESS', 'ALK EL', 'PEM FC', 'H2 Tank', 'PV', 'Onshore WT'],
    usecols='V:Y',
    skiprows=[0, 1],
    nrows=3
)
```

Each sheet must include an `avg` column with average prices for the reference years:
- 2020
- 2030
- 2050

---

## Decision variables and discretization

System sizing is performed using discretized variables defined in `comp_dict`:

- Electrolyzer size
- Fuel cell size
- Battery energy capacity
- Hydrogen tank capacity
- PV installed capacity

Each variable is optimized as an integer multiple of a predefined resolution, ensuring realistic and modular system designs.

---

## How to run

From the repository root directory:

```bash
python main.py
```

The script will:
1. Load time series and economic data,
2. Perform degradation-aware simulations,
3. Run the stochastic optimization,
4. Save the optimal configuration and LCOS to a CSV file.

---

## Degradation modeling notes

The main script implements:
- Battery capacity fade through SOH-based fitting,
- Electrolyzer performance decay linked to operating conditions and battery degradation,
- Fuel cell performance decay through fitted empirical relationships,
- Lifetime estimation using performance threshold criteria.

These degradation trends are propagated into the reduced-order multi-year simulation.

---

## Reproducibility

For reproducible results:
- Fix random seeds where applicable,
- Archive the exact input data files used,
- Track Python and dependency versions.

