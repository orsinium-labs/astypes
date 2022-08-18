from __future__ import annotations

from enum import Enum


class Ass(Enum):
    """Assumptions about the types that might be not true but usually are true.
    """
    # cannot infer type of one or more of the return statements,
    # assume all return statements to have the same type.
    # It is here for the sake of infer-types.
    ALL_RETURNS_SAME = 'all-returns-same'
    # assume that comparison operations aren't overloaded
    NO_COMP_OVERLOAD = 'no-comp-overload'
    # assume that unary operators aren't overloaded
    NO_UNARY_OVERLOAD = 'no-unary-overload'
    # assume that all CamelCase names are types
    CAMEL_CASE_IS_TYPE = 'camel-case-is-type'
    # assume that built-in types and functions aren't shadowed
    NO_SHADOWING = 'camel-case-is-type'
