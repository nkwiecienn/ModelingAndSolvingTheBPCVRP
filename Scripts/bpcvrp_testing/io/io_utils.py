from __future__ import annotations

from pathlib import Path
from typing import Protocol, Union

from instances import BPPInstance
from instances import VRPInstance


PathLike = Union[str, Path]


class HasToDzn(Protocol):
    def to_dzn(self) -> str: ...


def load_txt_bpp(path: PathLike) -> BPPInstance:
    p = Path(path)
    return BPPInstance.from_txt(str(p))


def load_txt_vrp(path: PathLike) -> VRPInstance:
    p = Path(path)
    return VRPInstance.from_txt(str(p))


def save_as_dzn(instance: HasToDzn, path: PathLike) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    dzn_text = instance.to_dzn()
    p.write_text(dzn_text, encoding="utf-8")
