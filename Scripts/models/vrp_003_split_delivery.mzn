include "globals.mzn";

%========================
% Input
%========================

int: N;                         % number of customers
int: Capacity;                  % vehicle capacity
array[1..N] of int: Demand;     % demand of each customer

% Distance matrix from generator: size (N+1)x(N+1)
% Interpretation here: index 1 is depot, indices 2..N+1 are customers 1..N.
array[1..N+1, 1..N+1] of int: Distance;

int: nbVehicles;                % upper bound on number of vehicles
int: maxVisitsPerCustomer;      % number of copy-nodes per customer (visit bound)

% Derived bound for time variables (same spirit as benchmark models)
int: timeBudget = sum(i in 1..N+1)( max(j in 1..N+1)(Distance[i,j]) );

set of int: CUSTOMER = 1..N;
set of int: VEHICLE  = 1..nbVehicles;
set of int: LOAD     = 0..Capacity;
set of int: TIME     = 0..timeBudget;

%========================
% Giant-tour indexing
%========================

int: nbCustomerCopies = N * maxVisitsPerCustomer;
set of int: CUSTOMER_COPIES = 1..nbCustomerCopies;

int: firstStartDepot = nbCustomerCopies + 1;
int: firstEndDepot   = nbCustomerCopies + nbVehicles + 1;
int: lastNode        = nbCustomerCopies + 2*nbVehicles;

set of int: NODES = 1..lastNode;

set of int: START_DEPOT_NODES = firstStartDepot .. (firstStartDepot + nbVehicles - 1);
set of int: END_DEPOT_NODES   = firstEndDepot   .. (firstEndDepot   + nbVehicles - 1);
set of int: DEPOT_NODES       = START_DEPOT_NODES union END_DEPOT_NODES;

function int: origCustomer(int: n) =
  1 + ((n - 1) div maxVisitsPerCustomer);

function bool: isCopy(int: n)  = n in CUSTOMER_COPIES;
function bool: isDepot(int: n) = n in DEPOT_NODES;

% Map a giant-tour node to the base Distance index:
% depot -> 1, customer c -> c+1
function int: baseIndex(int: n) =
  if isDepot(n) then 1 else origCustomer(n) + 1 endif;

% Precomputed distances on the giant-tour nodes:
% - depot-to-depot connector arcs are 0
% - same-customer copy-to-copy arcs are 0 (same location)
array[NODES, NODES] of int: distance =
  array2d(NODES, NODES,
    [ if isDepot(a) /\ isDepot(b) then 0
      elseif isCopy(a) /\ isCopy(b) /\ origCustomer(a) = origCustomer(b) then 0
      else Distance[baseIndex(a), baseIndex(b)]
      endif
    | a in NODES, b in NODES ]);

%========================
% Decision variables
%========================

array[NODES] of var NODES: successor;
array[NODES] of var NODES: predecessor;

array[NODES] of var VEHICLE: vehicle;

array[NODES] of var LOAD: load;
array[NODES] of var TIME: arrivalTime;

% Delivered quantity at a node:
% - depots deliver 0
% - inactive copy-nodes (self-loop) deliver 0
array[NODES] of var 0..Capacity: delivered;

var int: objective;

%========================
% Initialisation constraints (same idea as your CVRP)
%========================

% predecessor links for start depots (closing the ring of depot nodes)
constraint forall(v in 2..nbVehicles)(
  predecessor[firstStartDepot + (v-1)] = firstEndDepot + (v-2)
);
constraint predecessor[firstStartDepot] = firstEndDepot + (nbVehicles - 1);

% successor links for end depots (closing the ring of depot nodes)
constraint forall(v in 1..nbVehicles-1)(
  successor[firstEndDepot + (v-1)] = firstStartDepot + v
);
constraint successor[firstEndDepot + (nbVehicles - 1)] = firstStartDepot;

% associate depot nodes with vehicle indices
constraint forall(v in 1..nbVehicles)(
  vehicle[firstStartDepot + (v-1)] = v /\
  vehicle[firstEndDepot   + (v-1)] = v
);

% vehicles leave the depot at time 0, and load starts at 0
constraint forall(n in START_DEPOT_NODES)(arrivalTime[n] = 0);
constraint forall(n in START_DEPOT_NODES)(load[n] = 0);

% depots deliver nothing
constraint forall(n in DEPOT_NODES)(delivered[n] = 0);

%========================
% Successor / predecessor consistency + optional copies
%========================

constraint redundant_constraint(
  forall(n in NODES)(successor[predecessor[n]] = n)
);
constraint redundant_constraint(
  forall(n in NODES)(predecessor[successor[n]] = n)
);

% customer copies may be inactive via self-loop
constraint subcircuit(successor);

% depot nodes are always active (already implied by fixed connectors, but explicit is fine)
constraint forall(n in DEPOT_NODES)(successor[n] != n);

%========================
% Split-delivery constraints (new part)
%========================

% inactive copy -> no delivery
constraint forall(n in CUSTOMER_COPIES)(
  (successor[n] = n) -> (delivered[n] = 0)
);

% active copy -> deliver something (prevents pointless visits)
constraint forall(n in CUSTOMER_COPIES)(
  (successor[n] != n) -> (delivered[n] >= 1)
);

% no copy can deliver more than the total demand of its customer
constraint forall(n in CUSTOMER_COPIES)(
  delivered[n] <= Demand[origCustomer(n)]
);

% satisfy demand by summing deliveries across copies
constraint forall(c in CUSTOMER)(
  sum(n in CUSTOMER_COPIES where origCustomer(n) = c)(delivered[n]) = Demand[c]
);

%========================
% Vehicle propagation (only through active copies)
%========================

constraint forall(n in CUSTOMER_COPIES)(
  (successor[n] != n) ->
    ( vehicle[predecessor[n]] = vehicle[n] /\
      vehicle[successor[n]]   = vehicle[n] )
);

%========================
% Time and load propagation
%========================

constraint forall(n in CUSTOMER_COPIES)(
  arrivalTime[n] + distance[n, successor[n]] <= arrivalTime[successor[n]]
);
constraint forall(n in START_DEPOT_NODES)(
  arrivalTime[n] + distance[n, successor[n]] <= arrivalTime[successor[n]]
);

constraint forall(n in CUSTOMER_COPIES)(
  load[n] + delivered[n] = load[successor[n]]
);
constraint forall(n in START_DEPOT_NODES)(
  load[n] = load[successor[n]]
);

%========================
% Objective (same style as your CVRP chapter)
%========================

constraint objective = sum(d in END_DEPOT_NODES)(arrivalTime[d]);

solve minimize objective;

%========================
% Output (keep it simple for debugging)
%========================

output [
  "objective = ", show(objective), ";\n",
  "successor = ", show(successor), ";\n",
  "predecessor = ", show(predecessor), ";\n",
  "vehicle = ", show(vehicle), ";\n",
  "delivered = ", show(delivered), ";\n",
  "load = ", show(load), ";\n",
  "arrivalTime = ", show(arrivalTime), ";\n"
];
