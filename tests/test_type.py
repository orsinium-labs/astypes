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
    assert given.signature == expected


@pytest.mark.parametrize('given, expected', [
    (t(''), []),
    (t('int'), []),
    (
        t('Iterator', module='typing'),
        ['from typing import Iterator'],
    ),
    (
        t('list', args=[t('Iterator', module='typing')]),
        ['from typing import Iterator'],
    ),
    (
        u('list', t('Iterator', module='typing')),
        ['from typing import Iterator'],
    ),
])
def test_imports(given: Type, expected: str):
    assert given.imports == frozenset(expected)
    assert given.assumptions == frozenset()


@pytest.mark.parametrize('left, right, expected', [
    (t('int'), t('int'), True),
    (t('Any'), t('int'), True),
    (t('object'), t('int'), True),
    (t('float'), t('int'), True),
    (u('int', 'str'), t('int'), True),
    (u('str', 'int'), t('int'), True),

    (t('str'), t('int'), False),
    (t('int'), t('float'), False),
    (u('str', 'int'), t('bytes'), False),
])
def test_supertype_of(left: Type, right: Type, expected: bool):
    assert left.supertype_of(right) is expected
