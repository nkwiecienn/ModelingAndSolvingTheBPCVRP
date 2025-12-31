% runs out of time around n = 100, c = 150

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
array[B, I] of var bool: x;            % item i assigned to bin j
var 0..m: nBins;                       % number of used bins

% ---------------- Constraints ----------------

constraint bin_packing(capacity, b, size);                                         % load of each bin smaller than c
constraint forall(i in I, j in B)(x[j, i] <-> (b[i] = j));                         % channeling between x and b
constraint forall(j in 1..m-1)(lex_greatereq(x[j,..], x[j+1,..]));                 % sorting lexicographically
constraint forall(i in I)(b[i] <= i);                                              % item i is packed into bin with index <= i
constraint forall(i, k in I where i < k /\ size[i] = size[k])(b[i] <= b[k]);       % for items with the same size, earlier index is not in a later bin
constraint nBins = max(i in I)(b[i]);                                              % define number of bins
% ---------------- Search ----------------
solve minimize nBins;