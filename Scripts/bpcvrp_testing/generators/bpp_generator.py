from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import random
from math import floor, ceil

from ..instances.bpp_instance import BPPInstance


def generate_random_bpp(
    n: int,
    capacity: int,
    min_ratio: float = 0.2,
    max_ratio: float = 0.8,
    seed: Optional[int] = None,
) -> BPPInstance:
    """Generate a random Bin Packing Problem (BPP) instance.

    - number of items = ``n``
    - bin capacity = ``capacity``
    - item sizes are sampled uniformly from
      [min_ratio * capacity, max_ratio * capacity] and rounded to ints.

    Example
    -------
    >>> inst = generate_random_bpp(
    ...     n=50,
    ...     capacity=100,
    ...     min_ratio=0.2,
    ...     max_ratio=0.8,
    ...     seed=123,
    ... )
    >>> inst.n, inst.capacity, inst.sizes[:5]

    Parameters
    ----------
    n : int
        Number of items. Must be > 0.
    capacity : int
        Bin capacity (corresponds to `binCapacity` in the model). Must be > 0.
    min_ratio : float
        Lower bound for item size as a fraction of `capacity` (e.g. 0.2).
        Must be in (0, 1].
    max_ratio : float
        Upper bound for item size as a fraction of `capacity` (e.g. 0.8).
        Must be in (0, 1] and `max_ratio >= min_ratio`.
    seed : int | None
        RNG seed. If ``None``, the generator uses the global random state.

    Returns
    -------
    BPPInstance
        Generated bin packing instance.
    """

    rng = random.Random(seed)

    min_size = max(1, floor(min_ratio * capacity))
    max_size = min(capacity, ceil(max_ratio * capacity))

    if min_size > max_size:
        min_size = max_size = 1

    sizes: List[int] = [
        rng.randint(min_size, max_size) for _ in range(n)
    ]

    sizes.sort(reverse=True)

    return BPPInstance(
        n=n,
        capacity=capacity,
        sizes=sizes,
    )
