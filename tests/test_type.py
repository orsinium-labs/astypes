from __future__ import annotations
import pytest
from astypes import Type

t = Type.new


def u(*args):
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            arg = t(arg)
        new_args.append(arg)
    return t('Union', args=new_args)


@pytest.mark.parametrize('left, right, result', [
    # simplify the same type twice
    ('float',   'float',    'float'),
    ('str',     'str',      'str'),

    # simplify int+float
    ('float',   'int',      'float'),
    ('int',     'float',    'float'),
    ('int',     'int',      'int'),

    # simplify one unknown
    ('',        'int',      'int'),
    ('int',     '',         'int'),
    ('',        '',         ''),

    # actual unions
    ('str',     'int',      u('str', 'int')),
    ('int',     'str',      u('int', 'str')),
    ('int',     'None',     u('int', 'None')),
    ('None',    'int',      u('int', 'None')),

    # unwrap nested unions
    (u('str', 'bool'), 'int', u('str', 'bool', 'int')),
    ('int', u('str', 'bool'), u('int', 'str', 'bool')),
    (u('str', 'bool'), u('int', 'bytes'), u('str', 'bool', 'int', 'bytes')),
    (u('str', 'float'), 'int', u('str', 'float')),
    (u('float', 'str'), 'int', u('float', 'str')),
])
def test_merge(left, right, result):
    if isinstance(left, str):
        left = t(left)
    if isinstance(right, str):
        right = t(right)
    if isinstance(result, str):
        result = t(result)
    assert left.merge(right) == result


@pytest.mark.parametrize('given, expected', [
    (t('int'),                      'int'),
    (u('int', 'str'),               'int | str'),
    (t('list', args=[t('int')]),    'list[int]'),
    (t(''),                         'Any'),
])
def test_annotation(given: Type, expected: str):
    assert given.annotation == expected
