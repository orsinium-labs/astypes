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

    # operations with known type
    ('not x',       'bool'),
    ('x is str',    'bool'),
    ('x and y',     'bool'),
    ('x or y',      'bool'),

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
])
def test_cannot_infer_expr(expr):
    node = astroid.extract_node(expr)
    assert get_type(node) is None


@pytest.mark.parametrize('setup, expr, type', [
    ('import math',                 'math.sin(x)',  'float'),
    ('from math import sin',        'sin(x)',       'float'),
    ('my_list = list',              'my_list(x)',   'list'),
    ('def g(x): return 0',          'g(x)',         'int'),
    ('def g(x) -> int: return x',   'g(x)',         'int'),
])
def test_astroid_inference(tmp_path, setup, expr, type):
    stmt = astroid.parse(f'{setup}\n{expr}').body[-1]
    assert isinstance(stmt, astroid.Expr)
    t = get_type(stmt.value)
    assert t is not None
    assert t.annotation == type
