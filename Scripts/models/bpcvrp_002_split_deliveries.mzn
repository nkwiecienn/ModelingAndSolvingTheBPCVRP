include "subcircuit.mzn";
include "bin_packing.mzn";
include "lex_greatereq.mzn";

% ------------------------------------------------------------
% Core CVRP input
% ------------------------------------------------------------
int: N;                       % number of customers
int: Capacity;                % vehicle capacity (here: in pallets)
array[1..N+1, 1..N+1] of int: Distance;  % depot is index 1, customers are 2..N+1

int: nbVehicles;
int: maxVisitsPerCustomer;

set of int: CUSTOMER = 1..N;
set of int: VEHICLE  = 1..nbVehicles;

% A safe time horizon built only from customer–customer distances
int: timeBudget = sum(i in 2..N+1)(max([Distance[i,j] | j in 2..N+1]));
set of int: TIME = 0..timeBudget;
set of int: LOAD = 0..Capacity;

% ------------------------------------------------------------
% Packing input (per customer)
% ------------------------------------------------------------
array[1..N] of int: ItemsPerCustomer;
int: maxItemsPerCustomer;
int: binCapacity;  % pallet capacity (in item size units)
array[CUSTOMER, 1..maxItemsPerCustomer] of int: SizesOfItems;

set of int: Items = 1..maxItemsPerCustomer;
set of int: Bins  = 1..maxItemsPerCustomer;

% ------------------------------------------------------------
% BIN PACKING LAYER (per customer)
% ------------------------------------------------------------
array[CUSTOMER, Items] of var Bins: B;
array[CUSTOMER, Bins, Items] of var bool: X;

% This is the “bridge” quantity: number of pallets required by customer c
array[CUSTOMER] of var 0..maxItemsPerCustomer: Demand;

% Optional cleanup: padded items (i > ItemsPerCustomer[c]) stay in bin 1
constraint forall(c in CUSTOMER, i in Items where i > ItemsPerCustomer[c]) (
  B[c,i] = 1
);

% Feasibility of packing (only real items are relevant)
constraint forall(c in CUSTOMER)(
  bin_packing(
    binCapacity,
    B[c, 1..ItemsPerCustomer[c]],
    SizesOfItems[c, 1..ItemsPerCustomer[c]]
  )
);

% Channeling
constraint forall(c in CUSTOMER, i in Items, b in Bins)(
  X[c,b,i] <-> (B[c,i] = b)
);

% Symmetry breaking (same idea as in your BPP section)
constraint forall(c in CUSTOMER)(
  forall(b in 1..maxItemsPerCustomer-1)(
    lex_greatereq(X[c,b,..], X[c,b+1,..])
  )
);

% Count used bins = pallets (ignore padded items in the counting)
constraint forall(c in CUSTOMER)(
  Demand[c] =
    count(b in Bins)(
      sum(i in 1..ItemsPerCustomer[c])(bool2int(X[c,b,i])) > 0
    )
);

% ------------------------------------------------------------
% SPLIT-DELIVERY GIANT TOUR LAYER
% ------------------------------------------------------------
int: nbCustomerCopies = N * maxVisitsPerCustomer;
set of int: CUSTOMER_COPIES = 1..nbCustomerCopies;

% Node indexing:
%  1..nbCustomerCopies                          : customer copies
%  nbCustomerCopies+1 .. +nbVehicles            : start depots
%  nbCustomerCopies+nbVehicles+1 .. +2*nbVehicles : end depots
int: firstStartDepot = nbCustomerCopies + 1;
int: firstEndDepot   = nbCustomerCopies + nbVehicles + 1;
int: lastNode        = nbCustomerCopies + 2*nbVehicles;

set of int: NODES = 1..lastNode;
set of int: START_DEPOT_NODES = firstStartDepot .. (firstStartDepot + nbVehicles - 1);
set of int: END_DEPOT_NODES   = firstEndDepot   .. (firstEndDepot   + nbVehicles - 1);
set of int: DEPOT_NODES = START_DEPOT_NODES union END_DEPOT_NODES;

function int: origCustomer(int: n) =
  1 + ((n - 1) div maxVisitsPerCustomer);

function bool: isDepot(int: n) = n in DEPOT_NODES;
function bool: isCopy(int: n)  = n in CUSTOMER_COPIES;

% Map any node to Distance indices: 1 = depot, 2..N+1 = customers
function int: loc(int: n) =
  if isDepot(n) then 1 else origCustomer(n) + 1 endif;

% Distance in giant tour:
% - depot-to-depot connectors treated as 0
% - copies of the same customer have 0 distance between them
function int: dist(int: a, int: b) =
  if isDepot(a) /\ isDepot(b) then 0
  elseif isCopy(a) /\ isCopy(b) /\ origCustomer(a) = origCustomer(b) then 0
  else Distance[loc(a), loc(b)]
  endif;

% ------------------------------------------------------------
% Routing decision variables
% ------------------------------------------------------------
array[NODES] of var NODES: successor;
array[NODES] of var NODES: predecessor;

array[NODES] of var VEHICLE: vehicle;
array[NODES] of var TIME: arrivalTime;
array[NODES] of var LOAD: load;

% Delivered pallets on each node (copies only; depots fixed to 0)
array[NODES] of var 0..Capacity: delivered;

% ------------------------------------------------------------
% Routing constraints
% ------------------------------------------------------------

% Depots must be active (subcircuit would otherwise allow self-loops)
constraint forall(n in DEPOT_NODES)(successor[n] != n /\ predecessor[n] != n);

% ---- depot cycle initialisation (same idea as your CVRP model)
constraint forall(n in (firstStartDepot+1 .. firstStartDepot+nbVehicles-1))(
  predecessor[n] = n + nbVehicles - 1
);
constraint predecessor[firstStartDepot] = lastNode;

constraint forall(n in (firstEndDepot .. lastNode-1))(
  successor[n] = n - nbVehicles + 1
);
constraint successor[lastNode] = firstStartDepot;

% ---- depot vehicle ids
constraint forall(n in START_DEPOT_NODES)(vehicle[n] = n - nbCustomerCopies);
constraint forall(n in END_DEPOT_NODES)(vehicle[n] = n - nbCustomerCopies - nbVehicles);

% ---- start depots
constraint forall(n in START_DEPOT_NODES)(
  arrivalTime[n] = 0 /\ load[n] = 0 /\ delivered[n] = 0
);
constraint forall(n in END_DEPOT_NODES)(delivered[n] = 0);

% ---- successor/predecessor consistency
constraint forall(n in NODES)(successor[predecessor[n]] = n);
constraint forall(n in NODES)(predecessor[successor[n]] = n);

constraint subcircuit(successor);
constraint subcircuit(predecessor);

% ---- deliveries: unused copy => 0; used copy => at least 1
constraint forall(n in CUSTOMER_COPIES)(
  (successor[n] = n) -> (delivered[n] = 0)
);
constraint forall(n in CUSTOMER_COPIES)(
  (successor[n] != n) -> (delivered[n] >= 1)
);

% ---- split-demand satisfaction (this is the key SD link)
constraint forall(c in CUSTOMER)(
  sum(n in CUSTOMER_COPIES where origCustomer(n) = c)(delivered[n]) = Demand[c]
);

% Feasibility guard (prevents “obviously impossible” demands)
constraint forall(c in CUSTOMER)(
  Demand[c] <= maxVisitsPerCustomer * Capacity
);

% ---- propagate vehicle id along the used part of the tour
constraint forall(n in CUSTOMER_COPIES)(
  (successor[n] != n) ->
    (vehicle[successor[n]] = vehicle[n] /\ vehicle[predecessor[n]] = vehicle[n])
);

% ---- time propagation (copies + start depots)
constraint forall(n in CUSTOMER_COPIES union START_DEPOT_NODES)(
  arrivalTime[n] + dist(n, successor[n]) <= arrivalTime[successor[n]]
);

% ---- load propagation (increasing “delivered so far”; do NOT propagate from end depots)
constraint forall(n in CUSTOMER_COPIES)(
  load[n] + delivered[n] = load[successor[n]]
);
constraint forall(n in START_DEPOT_NODES)(
  load[n] = load[successor[n]]
);

% ------------------------------------------------------------
% Objective
% ------------------------------------------------------------
var TIME: objective = sum(d in END_DEPOT_NODES)(arrivalTime[d]);
solve minimize objective;
