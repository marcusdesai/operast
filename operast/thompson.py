__all__ = [
    "Inst",
    "Unit",
    "UnitList",
    "AnyUnit",
    "UnitEq",
    "Match",
    "Jump",
    "Split",
    "thompson_vm",
    "vm_step",
]

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

UnitEq = Callable[[T, T], bool]


class Inst(Generic[T]):
    pass


@dataclass
class Unit(Inst[T]):
    __slots__ = ("e",)
    e: T


@dataclass
class UnitList(Inst[T]):
    __slots__ = ("ls",)
    ls: list[T]


@dataclass
class AnyUnit(Inst[T]):
    pass


@dataclass
class Match(Inst[T]):
    pass


@dataclass
class Jump(Inst[T]):
    __slots__ = ("goto",)
    goto: int


@dataclass
class Split(Inst[T]):
    __slots__ = "t1", "t2"
    t1: int
    t2: int


__NO_MATCH = object()


# todo: fix threading
# why not implement a JIT compiler that produces super-ops which reduce the
# number of epsilon transitions as much as possible.
def thompson_vm(program: list[Inst[T]], sequence: list[T], ident: UnitEq) -> bool:
    c_list: list[int] = [0]
    for item in [*sequence, __NO_MATCH]:
        step = vm_step(program, c_list, item, ident)
        if step is None:
            return True
        if len(step) == 0:
            return False
        c_list = step
    return False


def vm_step(
    program: list[Inst[T]], c_list: list[int], item: T, ident: UnitEq
) -> list[int] | None:
    n_list: list[int] = []
    for program_counter in c_list:
        inst = program[program_counter]
        if isinstance(inst, Unit):
            if item is __NO_MATCH or not ident(item, inst.e):
                continue
            n_list.append(program_counter + 1)
        elif isinstance(inst, UnitList):
            if item is __NO_MATCH or not any(ident(item, i) for i in inst.ls):
                continue
            n_list.append(program_counter + 1)
        elif isinstance(inst, AnyUnit):
            n_list.append(program_counter + 1)
        elif isinstance(inst, Match):
            return None
        elif isinstance(inst, Jump):
            c_list.append(inst.goto)
        elif isinstance(inst, Split):
            c_list.extend([inst.t1, inst.t2])
        else:  # pragma: no cover
            msg = "Unreachable!"
            raise ValueError(msg)
    return n_list
