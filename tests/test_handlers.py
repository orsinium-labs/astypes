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

    # methos of builtins
    ('"".join(x)',      'str'),
    ('[1,2].count(1)',  'int'),

    # builtin functions
    ('len(x)',          'int'),

    # comprehensions
    ('[x for x in y]',      'list'),
    ('{x for x in y}',      'set'),
    ('{x: y for x in z}',   'dict'),
])
def test_expr(expr, type):
    node = astroid.extract_node(f'None\n{expr}')
    t = get_type(node)
    assert t is not None
    assert t.signature == type


@pytest.mark.parametrize('expr', [
    'min(x)',
    'x',
    '+x',
    'x + y',
    'str.wat',
    '"hi".wat',
    'None.hi',
    'None.hi()',
    '"hi".wat()',
    'wat.wat',
])
def test_cannot_infer_expr(expr):
    node = astroid.extract_node(expr)
    assert get_type(node) is None


@pytest.mark.parametrize('setup, expr, type', [
    ('import math',             'math.sin(x)',  'float'),
    ('from math import sin',    'sin(x)',       'float'),
    ('my_list = list',          'my_list(x)',   'list'),
])
def test_astroid_inference(tmp_path, setup, expr, type):
    node = astroid.extract_node(f'{setup}\n{expr}')
    t = get_type(node)
    assert t.signature == type
