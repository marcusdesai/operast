__all__ = ["Ord", "OrdElem", "Partial", "Sib", "SibElem", "Total"]

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable, Iterator
from collections.abc import Iterable as Iter
from itertools import product
from typing import TypeAlias, TypeVar, Union, cast

T = TypeVar("T")

SibElem: TypeAlias = Union[str, "Sib"]


class Sib(list):
    """Constraint for tree node siblings"""

    __slots__ = ("loc",)

    def __init__(self, loc: int, *elems: SibElem) -> None:
        self.loc: int = loc
        list.__init__(self, self._flatten(elems))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sib):
            return False
        return self.loc == other.loc and all(
            a == b for a, b in zip(self, other, strict=True)
        )

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __repr__(self) -> str:
        elem_reprs = ", ".join(repr(e) for e in self)
        return f"{type(self).__name__}({self.loc}, {elem_reprs})"

    def _flatten(self, elems: tuple[SibElem, ...]) -> Iterator[SibElem]:
        for elem in elems:
            if isinstance(elem, Sib) and elem.loc == self.loc:
                yield from elem
            else:
                yield elem

    # Rules:
    #   1) Sib(x, A, B) => [Sib(x, A, B)]
    #   2) Sib(x, A, Sib(y, B, C)) => [Sib(x, A, B), Sib(y, B, C)]
    def constraint(self) -> list["Sib"]:
        ret = [self]
        for i, elem in enumerate(self):
            if isinstance(elem, Sib):
                flattened = elem.constraint()
                ret.extend(flattened)
                self[i] = flattened[0][0]
        return ret


OrdElem = Union[str, "Ord"]
StrTuples = str | tuple[str, ...]


def flatten_irregular(it: Iterable[T | Iterable[T]]) -> Iterator[T]:
    for i in it:
        if isinstance(i, Iter) and not isinstance(i, str):
            yield from i
        else:
            yield cast(T, i)


class Ord(ABC, list):
    """Constraint for tree node order"""

    def __init__(self, *elems: OrdElem) -> None:
        list.__init__(self, elems)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return list.__eq__(self, other)

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __repr__(self) -> str:
        elem_reprs = ", ".join(repr(e) for e in self)
        return f"{type(self).__name__}({elem_reprs})"

    @abstractmethod
    def _find_paths(self) -> Iterator[list[StrTuples]]:
        raise NotImplementedError

    def paths_product(self) -> Iterator[tuple[str, ...]]:
        for tup in product(*self._find_paths()):
            yield tuple(flatten_irregular(tup))

    def to_dag(self) -> dict[str, set[str]]:
        dag = defaultdict(set)
        for links in self.paths_product():
            for i, node in enumerate(links[:-1]):
                dag[node].add(links[i + 1])
            dag[links[-1]] = set()
        return dag


class Total(Ord):
    def _find_paths(self) -> Iterator[list[StrTuples]]:
        for e in self:
            yield [e] if isinstance(e, str) else list(e.paths_product())


class Partial(Ord):
    def _find_paths(self) -> Iterator[list[StrTuples]]:
        paths = (e.paths_product() if isinstance(e, Ord) else e for e in self)
        yield list(flatten_irregular(paths))
