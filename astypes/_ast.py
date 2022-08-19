import ast
from collections import deque
from inspect import getdoc
from typing import Iterator

import astroid


def walk(module: astroid.Module) -> Iterator[astroid.NodeNG]:
    stack = deque([module])
    while stack:
        node = stack.pop()
        doc_node = getattr(node, 'doc_node', None)
        if doc_node is not None and doc_node is not node:
            stack.append(doc_node)
        stack.extend(node.get_children())
        yield node


def find_node(module: astroid.Module, ast_node: ast.AST) -> astroid.NodeNG:
    if isinstance(ast_node, ast.Module):
        return module
    matches = []
    for node in walk(module):
        if node.lineno != ast_node.lineno:
            continue
        if node.col_offset != ast_node.col_offset:
            continue
        matches.append(node)
    if len(matches) == 1:
        return matches[0]

    if not matches:
        if isinstance(ast_node, ast.Expr):
            return find_node(module, ast_node.value)
        # different version of Python point either at the function start
        # or at the first decorator. Astroid is consistent.
        if isinstance(ast_node, ast.FunctionDef):
            for node in walk(module):
                if not isinstance(node, astroid.FunctionDef):
                    continue
                if node.name == ast_node.name:
                    return node

    node_name = type(ast_node).__name__
    doc_entry = f':class:`ast.{node_name}`'
    for match in matches:
        doc = getdoc(type(match))
        if doc is not None and doc_entry in doc:
            return match
    if matches:
        return matches[0]
    msg = f'no matches for {type(ast_node).__name__} node '
    msg += f'at {ast_node.lineno}:{ast_node.col_offset}'
    raise LookupError(msg)
