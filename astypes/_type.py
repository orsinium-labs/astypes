from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._ass import Ass


UNION = 'Union'


@dataclass(frozen=True)
class Type:
    _name: str
    _args: list[Type]
    _ass: set[Ass]
    _module: str

    @classmethod
    def new(
        cls,
        name: str, *,
        args: list[Type] | None = None,
        ass: set[Ass] | None = None,
        module: str = "",
    ):
        return cls(
            _name=name,
            _args=args or [],
            _ass=ass or set(),
            _module=module,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def args(self) -> tuple[Type, ...]:
        return tuple(self._args)

    @property
    def module(self) -> str:
        return self._module

    @cached_property
    def imports(self) -> frozenset[str]:
        result = set()
        if self._module:
            result.add(f'from {self.module} import {self._name}')
        for arg in self._args:
            result.update(arg.imports)
        return frozenset(result)

    @cached_property
    def assumptions(self) -> frozenset[Ass]:
        result = set()
        result.update(self._ass)
        for arg in self._args:
            result.update(arg.assumptions)
        return frozenset(result)

    @property
    def empty(self) -> bool:
        return not self._name

    @cached_property
    def signature(self) -> str:
        if self.name == UNION:
            return ' | '.join(arg.signature for arg in self._args)
        if self._args:
            args = ', '.join(arg.signature for arg in self._args)
            return f'{self._name}[{args}]'
        return self._name

    def merge(self, other: Type) -> Type:
        if self.empty:
            return other
        if other.empty:
            return self
        return type(self).new(
            name=UNION,
            args=[self, other],
        )

    def add_ass(self, ass: Ass) -> Type:
        return replace(self, _ass=self._ass | {ass})
