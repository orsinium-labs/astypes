import ast
from pathlib import Path
import astroid
import pytest
import astypes

ROOT = Path(astypes.__path__[0])
paths = [pytest.param(p, id=p.name) for p in ROOT.glob('*.py')]
UNSUPPORTED = (
    ast.alias, ast.expr_context,
    ast.arguments, ast.cmpop, ast.operator,
    ast.boolop, ast.unaryop, ast.comprehension,
)


@pytest.mark.parametrize('path', sorted(paths))
def test_smoke(path: Path):
    source = path.read_text()
    astroid_tree = astroid.parse(source)
    ast_tree = ast.parse(source)
    for ast_node in ast.walk(ast_tree):
        if isinstance(ast_node, UNSUPPORTED):
            continue
        astroid_node = astypes.find_node(astroid_tree, ast_node)
        if hasattr(ast_node, 'lineno'):
            assert astroid_node.lineno <= ast_node.lineno
