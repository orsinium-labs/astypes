from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Iterable, Union


try:
    from functools import cached_property
except ImportError:
    cached_property = property  # type: ignore


if TYPE_CHECKING:
    from ._ass import Ass


UNION = 'Union'
LITERAL = 'Literal'


@dataclass(frozen=True)
class Type:
    """The type of a Python expression.

    It is currently limited to what can be represented by type annotations.
    """
    _name: str
    _args: list[Type]   # arguments of the type for generic types
    _ass: set[Ass]      # assumptions that  were made to infer the type
    _module: str        # the module where the type is defined, empty for built-ins

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
    def fullname(self) -> str:
        """The full name of the type.

        For example, `typing.Iterable` or `list` (for builtins).
        """
        mod = self.module
        if mod:
            return f"{mod}.{self.name}"
        else:
            return self.name

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

    @property
    def is_union(self) -> bool:
        return self._name == UNION
    
    @property
    def is_literal(self) -> bool:
        """
        A literal type means it's literal values can be recovered with:
        
        >>> value1 = astroid.parse(type.args[0].name)
        """
        return self._name == LITERAL

    @cached_property
    def annotation(self) -> str:
        """Represent the type as a string suitable for type annotations.

        The string is a valid Python 3.10 expression.
        For example, `str | dict[str, Any]`.
        """
        if self.unknown:
            return 'Any'
        if self.is_union:
            return ' | '.join(arg.annotation for arg in self._args)
        if self._args:
            args = ', '.join(arg.annotation for arg in self._args)
            return f'{self._name}[{args}]'
        return self._name

    def replace(self, *, name: str | None = None,
        args: list[Type] | None = None,
        ass: set[Ass] | None = None,
        module: str | None = None,) -> Type:
        """
        Create a copy of the type with the updated attributes.
        """
        new_name = name if name is not None else self.name
        new_args = args if args is not None else self.args
        new_ass = ass if ass is not None else self._ass
        new_module = module if module is not None else self.module

        return Type.new(new_name, args=new_args, ass=new_ass, module=new_module)


    def merge(self, other: Type) -> Type:
        """Get a union of the two given types.

        If any of the types is unknown, the other is returned.
        When possible, the type is simplified. For instance, `int | int` will be
        simplified to just `int`.
        """
        if self.unknown:
            return other
        if other.unknown:
            return self
        if self.supertype_of(other):
            return self
        if other.supertype_of(self):
            return other

        # if one type is already union, extend it
        if self.is_union and other.is_union:
            return type(self).new(
                name=UNION,
                args=self._args + other._args,
                ass=self._ass | other._ass,
            )
        if self.is_union:
            return replace(self, _args=self._args + [other])
        if other.is_union:
            return replace(other, _args=[self] + other._args)

        # none goes last
        if self.name == 'None':
            args = [other, self]
        else:
            args = [self, other]
        return type(self).new(
            name=UNION,
            args=args,
        )

    def add_ass(self, ass: Ass) -> Type:
        """Get a copy of the Type with the given Ass added in the list of assertions.
        """
        return replace(self, _ass=self._ass | {ass})

    def supertype_of(self, other: Type) -> bool:
        if self.name == 'float' and other.name == 'int':
            return True
        if self.name in ('Any', 'object'):
            return True
        if self.is_union:
            for arg in self._args:
                if arg.supertype_of(other):
                    return True

        if self.name != other.name:
            return False
        if self.module != other.module:
            return False
        if self.args != other.args:
            return False
        return True


def merge_types(types:Iterable[Type]) -> Type:
    """
    Get a union of the given types.

    :see: `Type.merge`
    """
    types = list(types)
    if len(types)==1:
        return types[0]
    current_type = types.pop()
    for t in types:
        current_type = current_type.merge(t)
    return current_type

def union(*args:Union[Type, str]):
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            arg = Type.new(arg)
        new_args.append(arg)
    return Type.new('Union', args=new_args)