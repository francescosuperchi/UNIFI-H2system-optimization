# LCORE calculator: levelized cost of requested energy

This module implements **LCORE (Levelized Cost of Requested Energy)**, a modified version of LCOE where the energy term in the denominator is intended to represent **only the energy required by the load** (that is, excess generation is not credited).

The function is designed to be called from the sizing/optimization workflow where multi-year annual deficit outputs are already available from simulation.

---

## Citation

If this model is used in academic or technical work, please cite:

```text
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645
```

---

## What is included

- `LCORE_function(sizes, E_def_list, components, electricity, lifetime, hydrogen, r)`

It computes a discounted ratio:

- Numerator: discounted CAPEX + discounted O&M + discounted purchased electricity (deficit) costs
- Denominator: discounted requested/saved energy term (implemented in the code as `electricity['saved']`)

---

## Inputs and expected data structures

### `sizes` (dict)
Dictionary of component sizes. The function assigns these into `components[tech]['size']`.

Required keys:
- `EL` (kW)
- `FC` (kW)
- `BESS` (MWh)
- `HP_tank` (kg H2)
- `LP_tank` (kg H2)
- `PV` (kWp)
- `WT` (kW or kWp depending on upstream convention)
- `compressor` (unit size or binary in the upstream framework)

### `E_def_list` (list-like)
Annual electricity deficit to be purchased from the grid, with length equal to `lifetime`.

Unit convention: typically [MWh/y], consistent with `electricity['purchase price from grid']`.

### `components` (dict)
Dictionary of component techno-economic parameters. For each technology (for example `EL`, `FC`, `BESS`, etc.), the following fields are expected:

- `total installation costs` (currency per unit size)
- `OeM` (currency per unit size per year)
- `lifetime` (years)
- `relpacement` (fraction of CAPEX applied at replacement events)

Important: the key is spelled `relpacement` in the provided code and must match unless refactored.

### `electricity` (dict)
Dictionary containing the electricity price:

- `purchase price from grid` (currency per MWh)

The function also assigns internal fields:
- `excess`, `sold`, and `saved`

### `hydrogen` (dict)
Dictionary used by the wider framework. In this module it is only assigned:
- `produced [kg/y]`

### `lifetime` (int)
Economic analysis horizon in years. The function uses `N = lifetime + 1` years in the discounted cash-flow arrays.

### `r` (float)
Discount rate (for example `0.05` for 5%).

---

## Methodology details

### Discounting
For year index `n`:
- annual costs and energy are discounted by dividing by `(1 + r)**n`

### Replacement modelling
For each technology:
- replacement years are computed as multiples of `components[tech]['lifetime']` over a 20-year horizon (`np.arange(0, 20, lifetime)`)
- for each replacement year `n` (excluding 20), an additional discounted CAPEX is added:

```python
C_subs = size * total_installation_costs * relpacement
CAPEX_list[n] += C_subs / (1+r)**n
```

---

## Quick start

```python
from LCORE_calculator import LCORE_function

sizes = {
    "EL": 500, "FC": 500, "BESS": 5,
    "HP_tank": 2000, "LP_tank": 2000,
    "PV": 1000, "WT": 800, "compressor": 1,
}

components = {
    "EL": {"total installation costs": 800, "OeM": 20, "lifetime": 10, "relpacement": 0.4},
    "FC": {"total installation costs": 900, "OeM": 25, "lifetime": 10, "relpacement": 0.4},
    "BESS": {"total installation costs": 200000, "OeM": 5000, "lifetime": 10, "relpacement": 0.8},
    "HP_tank": {"total installation costs": 500, "OeM": 5, "lifetime": 25, "relpacement": 0.0},
    "LP_tank": {"total installation costs": 500, "OeM": 5, "lifetime": 25, "relpacement": 0.0},
    "PV": {"total installation costs": 600, "OeM": 10, "lifetime": 25, "relpacement": 0.0},
    "WT": {"total installation costs": 1200, "OeM": 30, "lifetime": 25, "relpacement": 0.0},
    "compressor": {"total installation costs": 60000, "OeM": 1500, "lifetime": 25, "relpacement": 0.0},
}

electricity = {"purchase price from grid": 165000}
hydrogen = {}

lifetime = 20
r = 0.05

E_def_list = [0.0] * lifetime  # example: no grid purchases

lcore = LCORE_function(sizes, E_def_list, components, electricity, lifetime, hydrogen, r)
print(lcore)
```

Note: numbers above are placeholders. Use values consistent with the rest of the framework.

---

## Notes and limitations

- In the provided code, the denominator energy term is set via:
  - `electricity['saved'] = 3007.74`
  This should be aligned with the intended definition of “requested energy” in the broader workflow.
- Excess generation is not credited in the denominator by design, consistent with the stated LCORE definition.
- The replacement-year logic currently assumes a 20-year horizon for replacement scheduling (`np.arange(0,20,...)`). If `lifetime` is not 20, consider aligning this with the passed `lifetime` argument for full generality.

---

