from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING


try:
    from functools import cached_property
except ImportError:
    cached_property = property  # type: ignore


if TYPE_CHECKING:
    from ._ass import Ass


UNION = 'Union'


@dataclass(frozen=True)
class Type:
    """The type of a Python expression.

    It is currently limited to what can be represented by type annotations.
    """
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
        """Construct a new Type.
        """
        return cls(
            _name=name,
            _args=args or [],
            _ass=ass or set(),
            _module=module,
        )

    @property
    def name(self) -> str:
        """The name of the type.

        For example, `Iterable` or `list`.
        """
        return self._name

    @property
    def args(self) -> tuple[Type, ...]:
        """Arguments of a generic type if any.

        For example, `(str, int)` if the type is `dict[str, int]`.
        """
        return tuple(self._args)

    @property
    def module(self) -> str:
        """The module where the type is defined.

        For example, `typing` if the type is `Iterable`.
        Empty string for built-ins.
        """
        return self._module

    @cached_property
    def imports(self) -> frozenset[str]:
        """Import statements required to define the type.
        """
        result = set()
        if self._module:
            result.add(f'from {self.module} import {self._name}')
        for arg in self._args:
            result.update(arg.imports)
        return frozenset(result)

    @cached_property
    def assumptions(self) -> frozenset[Ass]:
        """Assumptions that were made when inferring the type.
        """
        result = set()
        result.update(self._ass)
        for arg in self._args:
            result.update(arg.assumptions)
        return frozenset(result)

    @property
    def unknown(self) -> bool:
        """
        infer-types can create Type with empty name.
        It is used to denote an unknown type.
        """
        return not self._name

    @property
    def signature(self) -> str:
        """Alias for `Type.annotation`.
        """
        return self.annotation

    @cached_property
    def annotation(self) -> str:
        """Represent the type as a string suitable for type annotations.

        The string is a valid Python 3.10 expression.
        For example, `str | dict[str, Any]`.
        """
        if self.name == UNION:
            return ' | '.join(arg.annotation for arg in self._args)
        if self._args:
            args = ', '.join(arg.annotation for arg in self._args)
            return f'{self._name}[{args}]'
        return self._name

    def merge(self, other: Type) -> Type:
        """Returns a union of the two given types.

        If any of the types is unknown, the other is returned.
        """
        if self.unknown:
            return other
        if other.unknown:
            return self
        return type(self).new(
            name=UNION,
            args=[self, other],
        )

    def add_ass(self, ass: Ass) -> Type:
        return replace(self, _ass=self._ass | {ass})
