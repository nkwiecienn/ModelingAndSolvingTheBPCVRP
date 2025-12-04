# Modeling and Solving the Bin Packing Capacitated Vehicle Routing Problem

This repository provides an environment for generating, converting, solving, and benchmarking:

- **BPP** – Bin Packing Problem  
- **VRP** – Vehicle Routing Problem  
- **BPCVRP** – The integrated Bin Packing + Capacitated Vehicle Routing Problem  

The framework is written in **Python**, uses **MiniZinc** as the underlying solver engine, and is designed for both **research purposes** and **extensive experimentation** on automatically generated or benchmark instances.

---

## Repository Structure

BBCVRP/
├── Scripts/ # Python library: instances, generators, IO tools, solvers, experiments
│
├── BPP/ # MiniZinc model for the Bin Packing Problem
│ ├── bpp_002.mzn
│ └── README.md # Short description of the BPP model
│
├── VRP/ # MiniZinc model for the Vehicle Routing Problem
│ ├── vrp_002.mzn
│ └── README.md # Short description of the VRP model
│
└── BPCVRP/ # MiniZinc model integrating BPP + VRP
├── bpcvrp_001.mzn
└── README.md # Short description of the BPCVRP model


---

## Key Features

### Modular Python package
Located in `Scripts/`, the package provides:

- **Instance classes** (`BPPInstance`, `VRPInstance`, `BPCVRPInstance`)
- **Generators** for random BPP/VRP/BPCVRP instances
- **IO utilities** to load `.txt` and export `.dzn`
- **MiniZincRunner** – a unified API for executing MiniZinc models
- **Batch experiment tools** for running many instances at once

### Automated experiment pipeline
Generate → Convert → Solve → Collect → Export → Analyse  
All in one consistent workflow.

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
git clone https://github.com/<your-name>/BBCVRP.git
cd BBCVRP
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To run playground scripts:

```bash
python -m Scripts.playground.playground_bpcvrp
```
