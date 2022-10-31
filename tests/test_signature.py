import sys
import pytest
import astroid

from inspect import Signature
from astypes._signature import signature

posonlyargs = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")
typecomment = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")

@pytest.mark.parametrize('sig', (
    '()',
    '(*, a, b=None)',
    '(*, a=(), b)',
    '(a, b=3, *c, **kw)',
    '(f=True)',
    '(x=0.1, y=-2)',
    "(s='theory', t=\"con'text\")",
    ))
def test_function_signature(sig: str) -> None:
    """
    A round trip from source to inspect.Signature and back produces
    the original text.
    """
    mod = astroid.parse(f'def f{sig}: ...')
    func = mod['f']
    assert isinstance(func, astroid.FunctionDef)
    sig_instance = signature(func)
    assert isinstance(sig_instance, Signature)
    text = str(sig_instance)
    assert text == sig

@posonlyargs
@pytest.mark.parametrize('sig', (
    '(x, y, /)',
    '(x, y=0, /)',
    '(x, y, /, z, w)',
    '(x, y, /, z, w=42)',
    '(x, y, /, z=0, w=0)',
    '(x, y=3, /, z=5, w=7)',
    '(x, /, *v, a=1, b=2)',
    '(x, /, *, a=1, b=2, **kwargs)',
    ))
def test_function_signature_posonly(sig: str) -> None:
    test_function_signature(sig)

@pytest.mark.parametrize('sig', (
    '(*, a: int | None, b=...)',
    '(*, a: \'int | None\', b: Literal[...] = None)',
    '(a: str, b: Callable[..., Any] = 3, *c: int, **kw: Any) -> None',
    '(f: Literal[False, True] = True) -> bytes | str',
    "(s: Literal['theory'] = 'theory', t: Literal[\"con'text\"] = \"con'text\")",
    ))
def test_function_signature_types(sig: str) -> None:
    test_function_signature(sig)

@pytest.mark.parametrize('sig', (
    '(a, a)',
    ))
def test_function_badsig(sig: str) -> None:
    """When a function has an invalid signature, an error is logged and
    the empty signature is returned.
    Note that most bad signatures lead to a SyntaxError, which we cannot
    recover from. This test checks what happens if the AST can be produced
    but inspect.Signature() rejects the parsed parameters.
    """

    mod = astroid.parse(f'def f{sig}: ...')
    func = mod['f']
    assert isinstance(func, astroid.FunctionDef)
    with pytest.raises(ValueError):
        signature(func)