% a MILP model but better?

include "bin_packing.mzn";
include "lex_greatereq.mzn";

% ---------------- Parameters ----------------
int: n;                                % number of items 
int: capacity;                         % max bin capacity
array[1..n] of int: size;              % item sizes

int: m = n;                            % max bins (worst case)
set of int: I = 1..n;
set of int: B = 1..m;

% ---------------- Variables ----------------
array[I] of var B: b;                  % bin index for each item
array[B] of var 0..1: y;               % a bin is used
array[I, B] of var 0..1: x;            % item i assigned to bin j
array[B] of var 0..capacity: load;     % load of each bin

% ---------------- Constraints ----------------
constraint forall(i in I)(b[i] = sum(j in B)(j * x[i, j]));                      % channeling between x and b
constraint forall(j in B)(load[j] = sum(i in I)(size[i] * x[i, j]));             % defining load of each bin
constraint bin_packing(capacity, b, size);                                       % capacity is not exceeded
constraint forall(j in B)(load[j] <= capacity * y[j]);                           % capacity is not exceeded
constraint forall(i in I)(sum(j in B)(x[i, j]) == 1);                            % each item is packed in exactly one bin
constraint forall(j in 1..m-1)(y[j] >= y[j+1]);                                  % bins are used in increasing order of index (no holes)
constraint forall(j in 1..m-1)(lex_greatereq(x[..,j], x[..,j+1]));               % sorting lexicographically
constraint forall(i in I)(b[i] <= i);                                            % item i is packed into bin with index <= i
% ---------------- Search ----------------
var 0..m: nBins;
constraint nBins = sum(j in B)(y[j]);
solve minimize nBins;