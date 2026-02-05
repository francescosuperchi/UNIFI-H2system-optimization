# Li-ion battery operation + degradation (rainflow-based)

This module provides:
- a **battery operation model** that enforces SOC and C-rate constraints and includes SOC- and C-rate-dependent charge/discharge efficiency
- a **daily degradation model** based on **cycle counting (rainflow)** over the daily SOC trajectory and a DoD-to-EoL empirical relationship

In this version, rainflow cycle counting is performed using the external **`rainflow`** Python package (instead of a custom in-file implementation).

---

## Citation

If this model is used in academic or technical work, please cite:

```text
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645
```

---

## What changed compared to the internal-rainflow version

- The functions `reversals`, `extract_cycles`, and `count_cycles` are no longer needed.
- The module now depends on the external package `rainflow` and uses:

```python
rainflow.count_cycles(SOC_day, ndigits=3)
```

- The degradation bins are controlled by `ndigits` (rounding of cycle ranges), not by a fixed `binsize` argument in a custom implementation.

---

## What is implemented

### 1) Efficiency map as a polynomial surface: `eta(soc, c_rate, coeff)`

Returns battery efficiency as a function of:
- `soc` (state of charge, typically 0 to 1)
- `c_rate` (C-rate)
- `coeff` (polynomial coefficients)

The function evaluates a 2D polynomial (up to cubic in C-rate) and returns efficiency as a fraction (division by 100 is applied in code).

Used inside `battery_operation(...)` with two coefficient sets:
- `coeff_c` for charging efficiency
- `coeff_d` for discharging efficiency

The coefficients in the script are taken from the referenced IEEE source (see in-code comment).

### 2) Battery dispatch model: `battery_operation(...)`

Computes battery power exchange to compensate mismatch between renewable production and a target power level.

**Main features**
- SOC limits:
  - `SOC_max = 0.95`
  - `SOC_min = 0.15`
- C-rate limits:
  - charge: `C_rate_C_max = 1`
  - discharge: `C_rate_D_max = 3`
- Effective capacity depends on SOH:
  - `Cap_actual = Capacity * SOH_old`
- Round-trip losses represented using the SOC- and C-rate-dependent `eta(...)` function.
- Output power returned as the corrected net output after battery action.

**Inputs**
- `i`: time-step index
- `P_RES`: renewable production power
- `P_goal`: target power (load or dispatch setpoint)
- `Capacity`: nominal battery energy capacity
- `SOC_old`: previous SOC
- `SOH_old`: previous SOH
- `Degr`: cumulative degradation damage variable
- `SOC_day`: list/array of SOC samples for the current day (used for daily rainflow counting)
- `C_rate_day`: list/array of C-rate samples for the current day (passed in, not used in degradation in this file)
- `kWh_factor`: number of simulation steps per hour (for example 60 for minute data)

**Outputs**
- `P_output`: net output power after battery compensation
- `SOC_new`: updated SOC
- `SOH_new`: updated SOH
- `Degr`: updated degradation damage variable
- `C_rate_C`: charge C-rate used at this step (0 if discharging)
- `C_rate_D`: discharge C-rate used at this step (0 if charging)

**Daily degradation trigger**
At the end of each day, degradation is updated using the daily SOC trajectory:

```python
if (i+1) % (kWh_factor*24) == 0:
    Degr = Battery_degradation_day(SOC_day, Degr)
```

Then SOH is updated as:

```python
SOH_new = 1 - 0.3 * Degr
```

This corresponds to a 30% end-of-life capacity fade when `Degr = 1` (as implemented).

### 3) Daily degradation: `Battery_degradation_day(SOC_day, Degr)`

Computes incremental degradation damage using:
- rainflow cycle counting on `SOC_day` via `rainflow.count_cycles(..., ndigits=3)`
- an empirical DoD-to-EoL relationship of the form:

```python
EoL(DoD) = a * DoD**b
damage += cycles_at_DoD / EoL(DoD)
```

Only cycles with DoD greater than a minimum threshold are counted (`min_range = 0.01`).

**Important note about range resolution**
With `ndigits=3`, the cycle ranges returned by `rainflow.count_cycles` are rounded to 3 decimals. This controls the effective DoD resolution used in damage accumulation.

---

## Requirements

- Python 3.10+ (recommended)
- numpy
- rainflow

Install example:

```bash
pip install numpy rainflow
```

Note: `scipy` is imported in the file but not required for the functions shown here. It can be removed if unused elsewhere.

---

## Quick start

Schematic example showing how to call the dispatch model inside a time loop:

```python
from battery_model import battery_operation

kWh_factor = 60  # minute resolution
Capacity = 5000  # units consistent with the rest of the framework
SOC = 0.5
SOH = 1.0
Degr = 0.0

SOC_day = []
C_rate_day = []

for i in range(kWh_factor * 24):  # one day
    P_RES = 1000.0
    P_goal = 900.0

    P_out, SOC, SOH, Degr, Cc, Cd = battery_operation(
        i=i,
        P_RES=P_RES,
        P_goal=P_goal,
        Capacity=Capacity,
        SOC_old=SOC,
        SOH_old=SOH,
        Degr=Degr,
        SOC_day=SOC_day,
        C_rate_day=C_rate_day,
        kWh_factor=kWh_factor,
    )

    SOC_day.append(SOC)
    C_rate_day.append(max(Cc, Cd))
```

---

## Notes and limitations

- The SOC and C-rate limits are hard-coded; adapt them if different battery chemistry/operation is needed.
- SOH update is linear in the accumulated damage variable (`SOH = 1 - 0.3*Degr`), which is a simplified mapping.
- The daily degradation uses SOC-based DoD cycles only; temperature and calendar aging are not included in this implementation.
- The end-of-day condition uses `kWh_factor*24`. Ensure `kWh_factor` represents steps per hour in the calling simulation.
- `C_rate_day` is passed but not used in `Battery_degradation_day(...)` as provided.
- Changing the rainflow settings (for example `ndigits`) can change degradation accumulation slightly due to different DoD binning.

---
