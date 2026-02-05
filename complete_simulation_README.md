# Complete first-year simulation (physics-based) for degradation-aware sizing

This module implements the **complete (detailed) simulation** used for the **first year** of operation in the degradation-aware workflow. The first-year simulation is used to:
- compute operational KPIs (energy deficits/excess, self-consumption, conversion to H2, compressor energy)
- estimate end-of-year degradation endpoints (battery SOH; electrolyzer and fuel cell working hours and conversion factor trends)
- produce the parameters needed to run the fast multi-year “extra-simplified” simulations used in optimization

The function exposed by this file is:

- `complete_sim(df_data, s)`

---

## Citation

If this model is used in academic or technical work, please cite:

```text
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645
```

---

## Dependencies

- Python 3.10+ (recommended)
- numpy
- pandas

External component models imported by this module:
- `MODEL_EL_variable`:
  - `EL_model`, `EL_transit`
- `MODEL_FC_variable`:
  - `FC_model`, `FC_transit`
- `MODEL_battery_NMC`:
  - `battery_operation`

If running from the repository root, these modules must be importable (same folder or installed package).

---

## Inputs

### `df_data` (pandas DataFrame)

The complete simulation expects `df_data` to contain at least the following columns:

- `wind_power` (kW)
- `PV_power` (kW)
- `load` (kW)
- `temperature` (°C)
- `date` (timestamp-like, used for bookkeeping; not required by the core calculations shown)

### `s` (list-like design vector)

Design vector is interpreted as:

- `s[0]` = `EL_size` (number of electrolyzer cells)
- `s[1]` = `FC_size` (number of fuel cell “cells” in the code terminology, used as a multiplier of `FC_cell_power`)
- `s[2]` = `BESS_size` (battery capacity, consistent with the rest of the framework; treated as kWh in comments)
- `s[3]` = `Tank_size` (high-pressure tank capacity, kg H2 at 350 bar)
- `s[4]` = `PV_upgrade` (dimensionless scaling parameter applied as `P_pv * (1 + PV_upgrade/16)`)

A fixed low-pressure buffer tank is defined internally:
- `lp_tank = 10` (kg at 30 bar)

The simulation time resolution is fixed in the function:
- `kWh_factor = 60` (minute-resolution assumptions)

---

## High-level workflow

For each time step:
1. **RES power availability**
   - `P_RES = P_wind + P_pv * (1 + PV_upgrade/16)`

2. **Compressor power**
   - Multistage compression work is computed using a simplified thermodynamic model and converted to `l_compr_ms` [kWh/kg]
   - Compressor load is applied when the low-pressure tank is being emptied to the high-pressure tank

3. **Battery dispatch**
   - `battery_operation(...)` is called to shape `P_RES` toward the requested power `P_requested` (load + compressor if active)
   - SOC and SOH are updated; degradation is updated daily via the battery model

4. **Hydrogen chain (optional)**
   If `EL_size == 0` or `FC_size == 0`, the hydrogen chain is disabled and residual deficit/excess is recorded without EL/FC.
   Otherwise:
   - **Electrolyzer** converts excess power (above a minimum threshold) into H2:
     - power limits: `EL_P_min` and `EL_P_nom`
     - H2 produced is limited by the low-pressure tank free capacity
   - **Compression** transfers H2 from low-pressure tank to high-pressure tank when LP tank is near full
   - **Fuel cell** converts stored H2 to electricity during deficit events:
     - power limits: `FC_P_min` and `FC_P_nom`
     - H2 request limited by available stored H2 (LP + HP)

5. **Thermal transients**
   - Electrolyzer temperature updated via `EL_transit(...)`
   - Fuel cell temperature updated via `FC_transit(...)`

6. **Working hours tracking**
   - `EL_h_work` increments only when the electrolyzer is producing H2
   - `FC_h_work` increments only when the fuel cell is consuming H2

After the loop, annual totals and performance indicators are computed and returned as a one-row DataFrame.

---

## Outputs

The function returns a pandas DataFrame with one row, containing (non-exhaustive list):

### Component sizing and end-of-year states
- `BESS[MWh]` (battery capacity as returned)
- `SOH_final` (battery SOH end of year)
- `PV_power[kWp]` (scaled PV size proxy)
- `EL_n_cells`, `FC_n_cells`
- `HP_tank[kg]`, `LP_tank[kg]`

### Performance and degradation proxies
- `EL_CF[kg/MWh]`, `FC_CF[kg/MWh]` (average conversion factors during active periods, scaled to kg/MWh)
- `EL_CF_fin`, `FC_CF_fin` (conversion factors estimated at reference temperatures using accumulated working hours)
- `EL_h_work`, `FC_h_work`

### Hydrogen production/handling
- `H2_prod_EL[kg]` (total EL hydrogen produced)
- `H2_Comp [kg]` (total hydrogen compressed to high pressure)

### Energy accounting
- `E_RES[MWh]` (available RES energy)
- `E_deficit_RES[MWh]`, `E_excess_RES[MWh]` (mismatch with initial RES only)
- `E_BESS_deficit[MWh]`, `E_BESS_excess[MWh]` (after battery)
- `E_to_H2[MWh]` (electricity converted to hydrogen)
- `E_comp[MWh]` (compressor electricity consumption)
- `E_H2_deficit[MWh]`, `E_H2_excess[MWh]` (after hydrogen chain)

### Self-consumption metrics
- `RES_SC[%]`
- `BESS_SC[%]`
- `H2_SC[%]`

---

## Quick start

```python
import pickle
from complete_simulation import complete_sim

with open("df_load_and_power.pkl", "rb") as f:
    df_data = pickle.load(f)

# Example design vector: [EL_cells, FC_cells, BESS_capacity, HP_tank_kg, PV_upgrade]
s = [30, 60, 5000, 2000, 40]

out = complete_sim(df_data, s)
print(out.T)
```

---

## Notes and limitations

- `kWh_factor` is hard-coded to 60 (minute resolution). If using different time resolution, adapt the code or make it a parameter.
- The PV “upgrade” scaling uses `1 + PV_upgrade/16` and later outputs `PV_power[kWp] = 160 * (1 + PV_upgrade/16)`. This implies a base PV reference of 160 kWp and a scaling convention that must match upstream assumptions.
- The wind turbine size is not explicitly optimized in this function; it is embedded in the input wind power time series.
- The compressor control uses a simplified low-pressure tank fill/empty logic and a counter-based scheduling approach.
- Many intermediate lists are defined in the file; only aggregated annual metrics are returned. For debugging, consider optionally returning time series arrays.

