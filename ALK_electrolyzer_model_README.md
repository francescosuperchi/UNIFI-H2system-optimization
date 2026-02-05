# Alkaline electrolyzer (ALK) model (electrochemical + thermal)

Python implementation of a simplified **alkaline electrolyzer** model including:
- a **polarization-based electrochemical model** returning conversion factor and interpolants
- a **lumped thermal transient** model for electrolyzer temperature evolution
- optional plotting utilities for ideal curves and degradation effects

The electrolyzer model is used as a component within the degradation-aware hybrid system sizing framework described in the related paper.

---

## Citation

If this model is used in academic or technical work, please cite:

```text
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645
```

Electrolyzer model formulation is based on:

- https://doi.org/10.1016/j.renene.2023.03.077

---

## What is implemented

### 1) Electrochemical model: `EL_model(...)`

**Purpose**
- Build a simple linear polarization curve (two-point interpolation)
- Link hydrogen production to stack current (two-point interpolation)
- Provide a conversion factor to relate stack power to hydrogen production

**Inputs**
- `T_el`: electrolyzer temperature [°C]
- `h_work_tot`: cumulative operating hours [h]
- `n_cells`: number of cells in the stack
- `kWh_factor`: time-step conversion factor used in the system simulation (for example 60 for minute data)
- `i_array_ideal`, `V_array_ideal`: ideal current-density and voltage arrays (defaults provided)

**Outputs**
- `conv_factor`: conversion factor [kg/kWh] (as defined in the code)
- `f_i_V`: interpolant mapping stack current to cell voltage
- `f_H2_i`: interpolant mapping hydrogen flow to stack current
- `V_array`: updated voltage array including degradation and temperature effects

**Degradation effects included**
- **time degradation** through a voltage increase rate `V_degr` [V/h]
- **temperature effect** through `V_T` [V/°C] relative to a reference operating temperature

A voltage limit check is included (warning when the model exceeds 2.3 V per cell under the time-degradation-only contribution).

### 2) Thermal transient model: `EL_transit(...)`

**Purpose**
- Update electrolyzer temperature using a lumped-parameter energy balance:
  - heat generation from electrochemical losses: proportional to `(V_op - V_tn) * I_op * n_cells`
  - heat loss to ambient through a series thermal resistance network (convection + conduction)

**Inputs**
- `H2_prod`: hydrogen production setpoint / operation [kg/h] (consistent with `f_H2_i` definition)
- `f_i_V`, `f_H2_i`: interpolants from `EL_model(...)`
- `T_el`: current electrolyzer temperature [°C]
- `n_cells`: number of cells
- `T_ext`: ambient temperature [°C]
- `kWh_factor`: time-step conversion factor (used to compute the simulation step in seconds)

**Output**
- `Tx`: updated electrolyzer temperature [°C]

The model includes an optional insulation toggle (enabled by default in the script).

---

## File contents (high level)

- Global arrays:
  - `V_array_ideal`: ideal voltage endpoints
  - `i_array_ideal`: ideal current-density endpoints

- Main functions:
  - `EL_model(...)`
  - `EL_transit(...)`

- Optional plotting section (executed if `electrolyzer_plots = True`):
  - ideal polarization curve
  - ideal H2-production curve
  - voltage increase with temperature decrease
  - voltage increase with accumulated operating hours

---

## Requirements

- Python 3.10+ (recommended)
- numpy
- scipy

Optional plotting:
- matplotlib

Optional (only if running the provided color-gradient plotting code):
- colour

Install example:

```bash
pip install numpy scipy matplotlib colour
```

---

## Quick start

Example usage in a simulation loop (schematic):

```python
from your_module_file import EL_model, EL_transit

# initialization
T_el = 60.0
h_work_tot = 0.0
n_cells = 106
kWh_factor = 60
T_ext = 25.0

conv_factor, f_i_V, f_H2_i, V_array = EL_model(T_el, h_work_tot, n_cells, kWh_factor)

# for each time step:
H2_prod = 5.0  # kg/h (example)
T_el = EL_transit(H2_prod, f_i_V, f_H2_i, T_el, n_cells, T_ext, kWh_factor)
h_work_tot += 1.0 / kWh_factor  # example increment (hours)
```

Note: units and time-step conventions must be consistent with the calling framework.

---

## Notes and limitations

- The electrochemical model uses **two-point interpolation**, intended as a lightweight surrogate.
- Degradation is represented as a **voltage shift**, not a full mechanistic model.
- The thermal model is **lumped** and based on simplified geometry scaling assumptions.
- The plotting block uses `matplotlib.pyplot` directly and an external dependency (`colour`). If plots are not needed, set `electrolyzer_plots = False` or remove that section.

---

## License

Add the repository license in `LICENSE`. If distributing as a standalone module, consider adding:
- `CITATION.cff`
- `NOTICE` (optional) to clarify citation and third-party references.
