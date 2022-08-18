from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from functools import cached_property


UNION = 'Union'


class Ass(Enum):
    """Assumptions about the types that might be not true but usually are true.
    """
    # cannot infer type of one or more of the return statements,
    # assume all return statements to have the same type
    ALL_RETURNS_SAME = 'all-returns-same'
    # assume that comparison operations aren't overloaded
    NO_COMP_OVERLOAD = 'no-comp-overload'
    # assume that unary operators aren't overloaded
    NO_UNARY_OVERLOAD = 'no-unary-overload'
    # assume that all CamelCase names are types
    CAMEL_CASE_IS_TYPE = 'camel-case-is-type'
    # assume that built-in types and functions aren't shadowed
    NO_SHADOWING = 'camel-case-is-type'


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
