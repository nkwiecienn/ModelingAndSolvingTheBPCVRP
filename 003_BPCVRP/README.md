# Bin Packing + Vehicle Routing Problem (BPCVRP)

The **BPCVRP** is a combined optimization problem integrating:

1. **Bin Packing** (per-customer item packing into pallets)
2. **Vehicle Routing** (routing pallets to customers)

### Problem Idea

For each customer:
- Items must be packed into pallets using a BPP formulation  
- The number of pallets becomes the customer's **demand** in the VRP  
- The VRP then computes optimal delivery routes for vehicles transporting pallets

### Objective
Minimize total travel time/distance over all vehicle routes.