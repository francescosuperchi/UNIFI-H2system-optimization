# PEM fuel cell model (electrochemical + thermal)

Python implementation of a simplified **PEM fuel cell** model including:
- an electrochemical performance model based on a datasheet polarization curve
- a lumped thermal transient model for stack temperature evolution
- optional plotting utilities (disabled by default)

This fuel cell model is used as a component within the degradation-aware hybrid system sizing framework described in the related paper.

---

## Citation

If this model is used in academic or technical work, please cite:

```text
F. Superchi, A. Moustakis, G. Pechlivanoglou and A. Bianchini, Applied Energy, vol. 377, Part D, p. 124645, 2025.
"On the importance of degradation modeling for the robust design of hybrid energy systems including renewables and storage"
https://doi.org/10.1016/j.apenergy.2024.124645
```

---

## What is implemented

### 1) Electrochemical model: `FC_model(...)`

**Purpose**
- Use a reference polarization curve (current to voltage) to compute:
  - hydrogen consumption factor per kWh of electrical energy
  - interpolants linking current, voltage, and hydrogen request
- Apply simplified degradation modifiers for operating time and temperature

**Data source for ideal polarization curve**
The code includes an ideal voltage curve derived from a datasheet (commented in code):
- `I_array` in [A]
- `V_array_ideal` in [V]

**Inputs**
- `T_FC`: fuel cell temperature [°C]
- `h_work_tot`: cumulative operating hours [h]
- `n_stacks`: number of stacks
- `kWh_factor`: time-step conversion factor used in the system simulation (for example 60 for minute data)
- `V_array_ideal`: ideal stack voltage array (defaults provided)

**Outputs**
- `conv_factor`: hydrogen required per electrical energy output [kg/kWh]
- `f_i_V`: interpolant mapping current [A] to voltage [V] including degradation effects
- `f_H2_i`: interpolant mapping hydrogen request to operating current

**Degradation effects included**
- **time degradation** implemented as a voltage drop proportional to operating hours (`V_degr`)
- **temperature degradation** implemented as an additional voltage drop when operating below the reference temperature (`V_T`)

Notes:
- `V_degr` and `V_T` are scaled by the number of cells (`n_cells = 96`) in the script.
- The nominal conversion factor reference uses `FC_CF_nom = 59/1000` [kg/kWh] as used in the code.

### 2) Thermal transient model: `FC_transit(...)`

**Purpose**
- Update fuel cell temperature using a lumped-parameter energy balance:
  - heat generation is computed from deviation from the thermoneutral voltage (`V_tn - V_op`)
  - heat is lost to ambient through a simplified thermal resistance network (conduction + convection)

**Inputs**
- `H2_req`: hydrogen request / consumption [kg/h] (consistent with `f_H2_i` definition)
- `f_i_V`, `f_H2_i`: interpolants produced by `FC_model(...)`
- `T_FC`: current fuel cell temperature [°C]
- `n_stacks`: number of stacks
- `T_ext`: ambient temperature [°C]
- `kWh_factor`: time-step conversion factor (used to compute the simulation step in seconds)

**Output**
- `Tx`: updated fuel cell temperature [°C]

The script includes a simplified geometric scaling and an insulation layer in the thermal resistance model.

---

## File contents (high level)

- Global arrays:
  - `I_array`: current points [A]
  - `V_array_ideal`: corresponding ideal voltage points [V]

- Main functions:
  - `FC_model(...)`
  - `FC_transit(...)`

- Optional plotting section (executed only if `fc_plots = True`, default is `False`):
  - ideal polarization curve
  - ideal hydrogen request curve
  - voltage degradation with temperature
  - voltage degradation with accumulated operating hours

---


## Quick start

Example usage (schematic):

```python
from your_module_file import FC_model, FC_transit

# initialization
T_FC = 55.0
h_work_tot = 0.0
n_stacks = 96
kWh_factor = 60
T_ext = 25.0

conv_factor, f_i_V, f_H2_i = FC_model(T_FC, h_work_tot, n_stacks, kWh_factor)

# for each time step:
H2_req = 2.0  # kg/h (example)
T_FC = FC_transit(H2_req, f_i_V, f_H2_i, T_FC, n_stacks, T_ext, kWh_factor)
h_work_tot += 1.0 / kWh_factor  # example increment (hours)
```

Note: units and time-step conventions must be consistent with the calling framework.

---

## Notes and limitations

- The electrochemical model relies on a **tabulated datasheet curve** and interpolation.
- Degradation is represented as a **voltage shift**, not a detailed electrichemical model.
- The thermal model is **lumped** and uses simplified geometry and heat-transfer coefficients.
- The optional plotting block uses `matplotlib.pyplot` directly and `colour`. If plots are not needed, keep `fc_plots = False` or remove the plotting section.

---


