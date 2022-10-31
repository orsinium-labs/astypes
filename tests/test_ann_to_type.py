import pytest

import astroid
from astypes._ann_to_type import get_annotation

@pytest.mark.parametrize(
        ("source", "expected"), 
        [("var: typing.Generic[T]", ["Generic[T]","typing"]), 
        ("var: typing.Generic[T, _KV]", ["Generic[T, _KV]","typing"]),
        ("from typing import Generic\nvar: Generic[T]", ["Generic[T]","typing"]),
        ("from mod import _model as m\nfrom typing import Optional\nvar: m.TreeRoot[Optional[T]]", ["TreeRoot[Optional[T]]","typing,mod._model"]),
        ("var: dict[str, str]", ["dict[str, str]",'']),
        ("import typing as t\nvar: t.Union[dict[str, str], dict[str, int]]", ["dict[str, str] | dict[str, int]",'typing']),
        ("import typing as t\nvar: t.Literal[True, False]", ["Literal[True, False]",'typing']),
        ("import typing as t\nvar: t.Literal['string']", ["Literal['string']",'typing']),
        ("import typing as t\nvar: dict[t.Type, t.Callable[[t.Any], t.Type]]", ["dict[Type, Callable[Any, Type]]",'typing'])]
    )
def test_annoation_to_type(source:str, expected:str) -> None:
    mod = astroid.parse(source)
    type_annotation = get_annotation(mod.body[-1].annotation)
    assert not type_annotation.unknown
    imports = '\n'.join(type_annotation.imports)
    annotation, imports_contains = expected
    if annotation.startswith('Union'):
        assert type_annotation.is_union
    if annotation.startswith('Literal'):
        assert type_annotation.is_literal
    for i in imports_contains.split(','):
        assert i in imports, f"{i!r} not in {imports}"
    assert type_annotation.annotation == annotation
    
    # smoke test
    astroid.parse(type_annotation.annotation)
