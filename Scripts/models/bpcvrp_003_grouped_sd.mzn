% Heuristic VRP for pallet-groups after preprocessing:
% - Full-vehicle pallet groups are removed in Python and accounted as fixedCost.
% - Remaining pallet groups (each < Capacity) form a classical CVRP instance.

include "circuit.mzn";

% =========================
% Input (after preprocessing)
% =========================

int: N;                        % number of remaining pallet-groups (nodes excluding depot)
int: Capacity;                 % vehicle capacity in pallets
int: nbVehicles;               % vehicles available for the remaining pallet-groups

array[1..N] of int: Demand;    % demand (pallets) of each remaining group; each should satisfy Demand[i] < Capacity
array[1..N+1, 1..N+1] of int: Distance;   % distance/time matrix for depot + remaining groups
                                          % convention: index 1 is depot, indices 2..N+1 are the N remaining groups

int: fixedCost;                % constant cost/time from full-vehicle direct trips (computed in Python)

% A simple upper bound for arrival times (same spirit as vrp_002)
int: timeBudget = sum(i in 1..N+1)( max([Distance[i,j] | j in 1..N+1]) );

set of int: VEHICLE = 1..nbVehicles;
set of int: CUSTOMER = 1..N;
set of int: TIME = 0..timeBudget;
set of int: LOAD = 0..Capacity;

% Giant-tour representation nodes:
set of int: NODES = 1..N + 2*nbVehicles;
set of int: DEPOT_NODES = N+1 .. N+2*nbVehicles;
set of int: START_DEPOT_NODES = N+1 .. N+nbVehicles;
set of int: END_DEPOT_NODES = N+nbVehicles+1 .. N+2*nbVehicles;

% Adapt Demand to giant-tour representation
array[NODES] of int: demand = [
  if i <= N then Demand[i] else 0 endif
| i in NODES
];

% Adapt Distance to giant-tour representation
array[NODES, NODES] of int: distance =
  array2d(NODES, NODES, [
    if i <= N /\ j <= N then
      Distance[i+1, j+1]          % group -> group
    elseif i <= N /\ j > N then
      Distance[i+1, 1]            % group -> depot
    elseif i > N /\ j <= N then
      Distance[1, j+1]            % depot -> group
    else
      Distance[1, 1]              % depot -> depot (usually 0)
    endif
  | i, j in NODES ]);

% =========================
% Decision variables
% =========================

array[NODES] of var NODES: successor;
array[NODES] of var NODES: predecessor;        % redundant, helps readability/propagation
array[NODES] of var VEHICLE: vehicle;

array[NODES] of var LOAD: load;
array[NODES] of var TIME: arrivalTime;

var 0..(fixedCost + nbVehicles * timeBudget): objective;

% =========================
% Constraints
% =========================

% ------ initialisation constraints (same idea as vrp_002) ---- %

% predecessor of start nodes are end nodes (depot ring)
constraint redundant_constraint(
  forall(n in (N+2 .. N+nbVehicles)) (
    predecessor[n] = n + nbVehicles - 1
  )
);
constraint redundant_constraint(
  predecessor[N+1] = N + 2*nbVehicles
);

% successors of end nodes are start nodes (depot ring)
constraint forall(n in (N+nbVehicles+1 .. N+2*nbVehicles-1)) (
  successor[n] = n - nbVehicles + 1
);
constraint successor[N + 2*nbVehicles] = N + 1;

% associate each start/end depot node with a vehicle
constraint forall(n in START_DEPOT_NODES) (
  vehicle[n] = n - N
);
constraint forall(n in END_DEPOT_NODES) (
  vehicle[n] = n - N - nbVehicles
);

% vehicles leave depot at time zero
constraint forall(n in START_DEPOT_NODES) (
  arrivalTime[n] = 0
);

% load initialisation at depot
constraint forall(n in START_DEPOT_NODES) (
  load[n] = 0
);

% ------- predecessor/successor consistency + single tour ---- %

constraint redundant_constraint(
  forall(n in NODES) (
    successor[predecessor[n]] = n
  )
);
constraint redundant_constraint(
  forall(n in NODES) (
    predecessor[successor[n]] = n
  )
);

constraint circuit(successor);
constraint redundant_constraint(circuit(predecessor));

% ---- vehicle propagation along the tour ---- %

constraint redundant_constraint(
  forall(n in CUSTOMER) (
    vehicle[predecessor[n]] = vehicle[n]
  )
);
constraint forall(n in CUSTOMER) (
  vehicle[successor[n]] = vehicle[n]
);

% ----- time propagation ---- %

constraint forall(n in CUSTOMER) (
  arrivalTime[n] + distance[n, successor[n]] <= arrivalTime[successor[n]]
);
constraint forall(n in START_DEPOT_NODES) (
  arrivalTime[n] + distance[n, successor[n]] <= arrivalTime[successor[n]]
);

% ----- load propagation ---- %

constraint forall(n in CUSTOMER) (
  load[n] + demand[n] = load[successor[n]]
);
constraint forall(n in START_DEPOT_NODES) (
  load[n] = load[successor[n]]
);

% =========================
% Objective
% =========================

constraint
  objective = fixedCost + sum(depot in END_DEPOT_NODES)(arrivalTime[depot]);

solve minimize objective;

% =========================
% Output
% =========================

output
  [ "objective = ", show(objective), ";\n",
    "fixedCost = ", show(fixedCost), ";\n",
    "vehicle = ", show(vehicle), ";\n",
    "arrivalTime = ", show(arrivalTime), ";\n",
    "successor = ", show(successor), ";\n"
  ];
