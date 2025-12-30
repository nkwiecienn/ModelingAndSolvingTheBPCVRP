# Modeling and Solving the Bin Packing Capacitated Vehicle Routing Problem

This repository provides an environment for generating, converting, solving, and benchmarking:

- **BPP** - Bin Packing Problem  
- **VRP** - Vehicle Routing Problem  
- **BPCVRP** - The integrated Bin Packing + Capacitated Vehicle Routing Problem  

The framework is written in **Python**, uses **MiniZinc** as the underlying solver engine.


## Key Features

### Modular Python package
Located in `Scripts/`, the package provides:

- **Instance classes** (`BPPInstance`, `VRPInstance`, `BPCVRPInstance`)
- **Generators** for random BPP/VRP/BPCVRP instances
- **IO utilities** to load `.txt` and export `.dzn`
- **MiniZincRunner** - a unified API for executing MiniZinc models
- **Batch experiment tools** for running many instances at once

### Automated experiment pipeline
Generate → Convert → Solve → Collect → Export → Analyse  
All in one workflow.

### Playground for manual testing
A set of interactive scripts for testing small toy examples before scaling up.

---

## Requirements

- Python ≥ 3.10  
- MiniZinc ≥ 2.7.0  
- Recommended solver: **Chuffed** or **Gecode**

---

## Installation

Clone and initialise the environment:

```bash
git clone https://github.com/nkwiecienn/ModelingAndSolvingTheBPCVRP
cd BBCVRP
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To run playground scripts:

```bash
python -m Scripts.playground.playground_bpcvrp
```
