import astroid
import pytest

from astypes import get_type


@pytest.mark.parametrize('expr, type', [
    # literals
    ('1',       'int'),
    ('1.2',     'float'),
    ('"hi"',    'str'),
    ('f"hi"',   'str'),
    ('b"hi"',   'bytes'),
    ('""',      'str'),
    ('None',    'None'),
    ('True',    'bool'),

    # collection literals
    ('[]',      'list'),
    ('[1]',     'list'),
    ('()',      'tuple'),
    ('(1,)',    'tuple'),
    ('{}',      'dict'),
    ('{1:2}',   'dict'),
    ('{1,2}',   'set'),

    # collection constructors
    ('list()',      'list'),
    ('list(x)',     'list'),
    ('dict()',      'dict'),
    ('dict(x)',     'dict'),
    ('set()',       'set'),
    ('set(x)',      'set'),
    ('tuple()',     'tuple'),
    ('tuple(x)',    'tuple'),

    # other type constructors
    ('int()',       'int'),
    ('int(x)',      'int'),
    ('str()',       'str'),
    ('str(x)',      'str'),
    ('float()',     'float'),
    ('float(x)',    'float'),

    # math operations
    ('3 + 2',       'int'),
    ('3 * 2',       'int'),
    ('3 + 2.',      'float'),
    ('3. + 2',      'float'),
    ('3 / 2',       'float'),
    ('"a" + "b"',   'str'),

    # binary "bool" operations
    ('3 and 2',     'int'),
    ('3 or 2',      'int'),
    ('3. and 2.',   'float'),
    ('3. or 2.',    'float'),

    # operations with known type
    ('not x',       'bool'),
    ('x is str',    'bool'),

    # operations with assumptions
    ('x in (1, 2, 3)',  'bool'),
    ('x < 10',          'bool'),
    ('~13',             'int'),
    ('+13',             'int'),

    # methods of builtins
    ('"".join(x)',      'str'),
    ('[1,2].count(1)',  'int'),
    ('list(x).copy()',  'list'),
    ('[].copy()',       'list'),
    ('[].__iter__()',   'Iterator'),

    # builtin functions
    ('len(x)',          'int'),
    ('oct(20)',         'str'),

    # comprehensions
    ('[x for x in y]',      'list'),
    ('{x for x in y}',      'set'),
    ('{x: y for x in z}',   'dict'),
    ('(x for x in y)',      'Iterator'),

    # misc
    ('Some(x)',             'Some'),
])
def test_expr(expr, type):
    node = astroid.extract_node(f'None\n{expr}')
    t = get_type(node)
    assert t is not None
    assert t.annotation == type


@pytest.mark.parametrize('expr', [
    'min(x)',
    'x',
    'X',
    'WAT',
    'wat()',
    'WAT()',
    '+x',
    'x + y',
    '1 + y',
    'x + 1',
    '"a" + 1',
    'str.wat',
    '"hi".wat',
    'None.hi',
    'None.hi()',
    '"hi".wat()',
    'wat.wat',
    'super().something()',
    'len(x).something()',
    '[].__getitem__(x)',
    'x or y',
    'x and y',
    'x = None; x = b(); x',
    'def g() -> x: pass; g()',
])
def test_cannot_infer_expr(expr):
    node = astroid.extract_node(expr)
    assert get_type(node) is None


@pytest.mark.parametrize('setup, expr, type', [
    ('import math',                 'math.sin(x)',  'float'),
    ('from math import sin',        'sin(x)',       'float'),
    ('my_list = list',              'my_list(x)',   'list'),
    ('def g(x): return 0',          'g(x)',         'int'),
    ('x = 13',                      'x',            'int'),
    ('x = 1\nif x:\n  x=True',      'x',            'int | bool'),
    ('from datetime import *',      'date(1,2,3)',  'date'),
])
def test_astroid_inference(setup, expr, type):
    stmt = astroid.parse(f'{setup}\n{expr}').body[-1]
    assert isinstance(stmt, astroid.Expr)
    t = get_type(stmt.value)
    assert t is not None
    assert t.annotation == type


@pytest.mark.parametrize('sig, type', [
    ('a: int', 'int'),
    ('b, a: int, c', 'int'),
    ('b: float, a: int, c: float', 'int'),
    ('*, a: int', 'int'),
    ('a: int, /', 'int'),
    ('a: list', 'list'),

    # *args and **kwargs
    ('*a: int', 'tuple[int]'),
    ('*a: garbage', 'tuple'),
    ('*a', 'tuple'),
    ('**a: int', 'dict[str, int]'),
    ('**a: garbage', 'dict[str, Any]'),
    ('**a', 'dict[str, Any]'),

    # parametrized generics
    ('a: list[str]', 'list[str]'),
    ('a: list[garbage]', 'list'),
    ('a: dict[str, int]', 'dict[str, int]'),
    ('a: tuple[str, int, float]', 'tuple[str, int, float]'),
    ('a: tuple[str, garbage]', 'tuple'),
])
def test_infer_type_from_signature(sig, type):
    given = f"""
        def f({sig}):
            return a
    """
    func = astroid.parse(given).body[-1]
    assert isinstance(func, astroid.FunctionDef)
    stmt = func.body[-1]
    assert isinstance(stmt, astroid.Return)
    t = get_type(stmt)
    assert t is not None
    assert t.annotation == type


@pytest.mark.parametrize('sig', [
    '',
    'b',
    'b: int',
    'a',
    'a: garbage',
    'a: garbage[int]',
])
def test_cannot_infer_type_from_signature(sig):
    given = f"""
        def f({sig}):
            return a
    """
    func = astroid.parse(given).body[-1]
    assert isinstance(func, astroid.FunctionDef)
    stmt = func.body[-1]
    assert isinstance(stmt, astroid.Return)
    t = get_type(stmt)
    assert t is None
