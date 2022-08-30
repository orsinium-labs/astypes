from __future__ import annotations

import ast
from logging import getLogger

import astroid
import typeshed_client

from ._ass import Ass
from ._type import Type


logger = getLogger(__package__)


def infer(node: astroid.NodeNG) -> list:
    try:
        return list(node.infer())
    except astroid.InferenceError:
        return []


def qname_to_type(qname: str) -> Type:
    if qname.startswith('builtins.'):
        qname = qname.split('.')[-1]
    if qname == 'NoneType':
        qname = 'None'
    if '.' not in qname:
        return Type.new(qname)
    mod_name, _, obj_name = qname.rpartition('.')
    return Type.new(obj_name, module=mod_name)


def is_camel(name: str) -> bool:
    if not name:
        return False
    if not name[0].isupper():
        return False
    if not any(c.islower() for c in name):
        return False
    return True


def get_ret_type_of_fun(
    mod_name: str,
    fun_name: str,
) -> Type | None:
    """For the given module and function name, get return type of the function.
    """
    module = typeshed_client.get_stub_names(mod_name)
    if module is None:
        logger.debug(f'no typeshed stubs for module {mod_name}')
        return None
    fun_def = module.get(fun_name)
    if fun_def is None:
        logger.debug('no typeshed stubs for module')
        return None
    if not isinstance(fun_def.ast, ast.FunctionDef):
        logger.debug('resolved call target is not a function')
        return None
    ret_node = fun_def.ast.returns
    return conv_node_to_type(mod_name, ret_node)


def conv_node_to_type(
    mod_name: str,
    node: ast.AST | astroid.NodeNG | None,
) -> Type | None:
    """Resolve ast node representing a type annotation into a type.
    """
    import builtins
    import typing

    if node is None:
        logger.debug('no return type annotation for called function def')
        return None

    # for generics, keep it generic
    if isinstance(node, (ast.Subscript, astroid.Subscript)):
        return conv_node_to_type(mod_name, node.value)

    # for regular name, check if it is a typing primitive or a built-in
    name: str | None = None
    if isinstance(node, ast.Name):
        name = node.id
    if isinstance(node, astroid.Name):
        name = node.name
    if name is not None:
        if hasattr(builtins, name):
            return Type.new(name, ass={Ass.NO_SHADOWING})
        if name in typing.__all__:
            return Type.new(name, module='typing')
        logger.debug(f'cannot resolve {name} into a known type')
        return None

    logger.debug('cannot resolve return AST node into a known type')
    return None
