# Scripts – Python Toolkit for BPP, VRP, and BPCVRP

This directory contains the **main Python package** used by the BBCVRP framework.  
It provides all tools required to load, generate, convert, solve, and benchmark problem instances.

The module is structured as follows:

Scripts/
├── instances/ # Data classes: BPPInstance, VRPInstance, BPCVRPInstance
├── generators/ # Random instance generators for BPP, VRP, BPCVRP
├── io/ # load_txt_bpp, load_txt_vrp, save_as_dzn, other utilities
├── solvers/ # MiniZincRunner: unified API for running MiniZinc models
├── experiments/ # Batch experiment runner + CSV output utilities
└── playground/ # Interactive scripts for manual testing and debugging


---

## Components Overview

### 1. `instances/`
Core data structures representing instances of:
- **BPP** (capacity, item sizes)
- **VRP** (distances, demands, vehicle capacity)
- **BPCVRP** (integrated BPP+VRP with per-customer items)

Each class supports:
- `.to_dict()` for MiniZinc API
- `.to_dzn()` for exporting `.dzn`

---

### 2. `generators/`
Random instance generators:

- `generate_random_bpp`
- `generate_random_vrp`
- `generate_random_bpcvrp` (VRP + per-customer BPP)

Generators support ranges, ratios, instance types (uniform/clustered/mixed), and random seeds for reproducibility.

---

### 3. `io/`
Functions for reading and writing instance data:

- `load_txt_bpp(path)`
- `load_txt_vrp(path)`
- `save_as_dzn(instance, path)`

---

### 4. `solvers/`
The `MiniZincRunner` wrapper provides:

- model loading (`.mzn`)
- time limit control
- solver selection (e.g., Chuffed)
- structured result format (status, objective, solution dict, time)

---

### 5. `experiments/`
Batch tools for research automation:

- `run_batch(instances, model, solver)`  
- `save_results_csv(results, path)`

Used to run entire experiment suites and collect results into CSV.

---

### 6. `playground/`
Showcase of all features:

- loading `.txt` → `.dzn`
- generating random instances
- solving via MiniZincRunner
- running small toy experiments


---

## Usage Example

```python
from Scripts.generators.bpp_generator import generate_random_bpp
from Scripts.solvers.minizinc_runner import MiniZincRunner

inst = generate_random_bpp(n=20, capacity=100, seed=1)
solver = MiniZincRunner("BPP/bpp_002.mzn", "chuffed")
result = solver.solve_instance(inst, time_limit=30)

print(result.objective, result.status)
