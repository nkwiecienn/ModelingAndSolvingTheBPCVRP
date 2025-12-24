% from https://github.com/MiniZinc/minizinc-benchmarks/blob/master/cvrp/cvrp.mzn

% Changes to allow split-deliveries:
% (a) Parameters:
% - maxVisitsPerCustomer
% - nbVehicles - now equal to customers * maxVisitsPerCustomer
% - VEHICLE - add dummy vehicle for unused nodes
% - NODES - now must include additional copies of customers
% - demand - don't need that, will use delivered instead
% - distance - add copies and distance 0 between customer copies
% - CopiesOfCustomer - set of nodes being a copy of a customer
% - VEHICLE - add a dummy vehicle
% (b) Variables:
% - delivered[n] - if n is a depot delivered[n] = 0; else number of items delivered to the node, sum of delivered per copies of customer equal to demand
% (c) Constraints:
% - (1)-(4) - the idea is the same but the calculations might be different depending on how NODES is made
% - (5)-(8) - remain the same
% - (9)-(10) - remain the same (even if node is unused)
% - (11)-(12) - subcircuit
% - (13)-(14) - the same but dummy vehicles must be added
% - (15)-(16) - the same
% - (17)-(18) - changed for 'delivered'

include "circuit.mzn";

int: N; % number of nodes in the MIP model
int: Capacity; % maximum capacity of each vehicle

int: nbVehicles; % maximum number of vehicles
int: maxVisitsPerCustomer;
int: nbCustomers = N;
int: timeBudget = sum (i in 1..N) (max([ Distance[i,j] | j in 1..N]) ); % the maximal of time that we got

set of int: VEHICLE = 1..nbVehicles;
set of int: CUSTOMER = 1..nbCustomers;
set of int: TIME = 0..timeBudget;
set of int: LOAD = 0..Capacity;

% copies to allow for Split Deliveries
int: nbCustomerCopies = nbCustomers * maxVisitsPerCustomer;
set of int: CUSTOMER_COPIES = 1..nbCustomerCopies;

% Node indexing:
%  1..nbCustomerCopies                     : customer copies
%  nbCustomerCopies+1 .. +nbVehicles       : start depots
%  nbCustomerCopies+nbVehicles+1 .. +2V    : end depots
int: firstStartDepot = nbCustomerCopies + 1;
int: firstEndDepot   = nbCustomerCopies + nbVehicles + 1;
int: lastNode        = nbCustomerCopies + 2*nbVehicles;

set of int: NODES = 1..lastNode;
set of int: START_DEPOT_NODES = firstStartDepot .. (firstStartDepot + nbVehicles - 1);
set of int: END_DEPOT_NODES   = firstEndDepot   .. (firstEndDepot   + nbVehicles - 1);
set of int: DEPOT_NODES = START_DEPOT_NODES union END_DEPOT_NODES;

% Mapping from a copy node to its original customer
function int: origCustomer(int: n) =
  1 + ((n - 1) div maxVisitsPerCustomer);

function bool: isCopy(int: n) = n in CUSTOMER_COPIES;
function bool: isDepot(int: n) = n in DEPOT_NODES;

array[1..N] of int: Demand; % demand of each customer
array[1..N+1, 1..N+1] of int: Distance; % distance matrix from MIP model
% adapting distance matrix to giant tour representation
% Location index for Distance0 (0 for depot, customer index otherwise)
function int: loc(int: n) =
  if isDepot(n) then 0 else origCustomer(n) endif;

% Distance on NODES:
% - depot-to-depot connectors are treated as 0
% - copies of the same customer have distance 0 between them (same location)
function int: dist(int: a, int: b) =
  if isDepot(a) /\ isDepot(b) then 0
  elseif isCopy(a) /\ isCopy(b) /\ origCustomer(a) = origCustomer(b) then 0
  else Distance[loc(a), loc(b)]
  endif;

% =================================================%
% Variables
% =================================================%

array[NODES] of var NODES: successor; 
array[NODES] of var NODES: predecessor; % redundant predecessor variables
array[NODES] of var VEHICLE: vehicle; % which vehicle visits which customer?
array[NODES] of var LOAD: load; % load when arriving at node n in NODES
array[NODES] of var TIME: arrivalTime; % the time at which the vehicle serving node i will arrive at i

% Delivered quantity on each node:
% - depot nodes deliver 0
% - copy nodes deliver some part of their original customer's demand
array[NODES] of var 0..Capacity: delivered;
var 0..timeBudget: objective;

% =================================================%
% Constraints
% =================================================%

% ------ initialization constraints ---- %
% predecessor of start nodes are end nodes
constraint redundant_constraint(
   forall(n in (nbCustomers+2..nbCustomers+nbVehicles)) (
     predecessor[n] = n + nbVehicles-1
   )
);

constraint redundant_constraint(
   predecessor[nbCustomers+1] = nbCustomers+2*nbVehicles
);

% successors of end nodes are start nodes
constraint 
   forall(n in (nbCustomers+nbVehicles+1..nbCustomers+2*nbVehicles-1)) (
     successor[n] = n-nbVehicles+1 
   );
constraint
   successor[nbCustomers+2*nbVehicles] = nbCustomers+1;

% associate each start/end nodes with a vehicle
constraint 
   forall(n in START_DEPOT_NODES) (
     vehicle[n] = n-nbCustomers
   );
   
constraint 
   forall(n in END_DEPOT_NODES) (
     vehicle[n] = n-nbCustomers-nbVehicles
   );

% vehicles leave the depot at time zero
constraint 
   forall(n in START_DEPOT_NODES) (
     arrivalTime[n] = 0 
   );

% vehicle load when starting at the depot
constraint 
   forall(n in START_DEPOT_NODES) (
     load[n] = 0 % demand[n]
   );


% ------- predecessor/successor constraints --- %
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

% alldiff + subtour elimination constraints
constraint 
   circuit(successor);
constraint redundant_constraint(
   circuit(predecessor)
);


% ---- vehicle constraints ------------- %

% vehicle of node i is the same as the vehicle for the predecessor
constraint redundant_constraint(
   forall(n in CUSTOMER) (
      vehicle[predecessor[n]] = vehicle[n]
   )
);
constraint 
   forall(n in CUSTOMER) (
      vehicle[successor[n]] = vehicle[n]
   );


% ----- time constraints ------------ %

constraint 
   forall(n in CUSTOMER) (
      arrivalTime[n] + distance[n,successor[n]] <= arrivalTime[successor[n]]
   );
constraint
   forall(n in START_DEPOT_NODES) (
      arrivalTime[n] + distance[n,successor[n]] <= arrivalTime[successor[n]]
   );

% ----- load constraints ------------ %

constraint 
   forall(n in CUSTOMER) (
      load[n] + demand[n] = load[successor[n]]
   );
constraint
   forall(n in START_DEPOT_NODES) (
      load[n] = load[successor[n]] 
   );


% =====================================
% Objective
% =====================================

constraint
 objective = sum (depot in END_DEPOT_NODES) (arrivalTime[depot]);

solve :: seq_search([int_search([successor[j] | j in NODES], first_fail, indomain_split, complete),
               int_search(vehicle, first_fail, indomain_split, complete),
               int_search([arrivalTime[j] | j in NODES],first_fail, indomain_min, complete),
               int_search([load[j] | j in NODES], first_fail, indomain_min, complete)
              ])   
minimize objective; % traveltime



% ===================================== %
% Output
% ===================================== %

output 
   [ "objective = "] ++ [show(objective)] ++
   [ ";\nvehicle = " ] ++ [ show(vehicle) ]++
   [ ";\narrivalTime = " ] ++ 
   [ show(arrivalTime) ]  ++ 
   [ ";\nsuccessor = "] ++          [ show(successor) ] ++
%            | n in NODES  ++
   [ ";\n"]
;