from __future__ import annotations

import ast
from dataclasses import dataclass, field
from logging import getLogger
from typing import Callable, TypeVar

import astroid
import typeshed_client

from ._ass import Ass
from ._helpers import infer, is_camel, qname_to_type
from ._type import Type


logger = getLogger(__package__)
Handler = Callable[[astroid.NodeNG], 'Type | None']
T = TypeVar('T', bound=Handler)


@dataclass
class Handlers:
    _registry: list[tuple[type, Handler]] = field(default_factory=list)

    def get_type(self, node: astroid.NodeNG) -> Type | None:
        """Infer type of the given astroid node.

        If the type cannot be inferred, None is returned.
        Keep in mind that a number of assumptions can be made about the code
        in order to infer the type. Use `Type.assumptions` to see them.
        """
        for supported_type, handler in self._registry:
            if isinstance(node, supported_type):
                result = handler(node)
                if result is not None:
                    return result
        return None

    def register(self, t: type) -> Callable[[T], T]:
        def callback(handler):
            self._registry.append((t, handler))
            return handler
        return callback


handlers = Handlers()
get_type = handlers.get_type


@handlers.register(astroid.Const)
def _handle_const(node: astroid.Const) -> Type | None:
    if node.value is None:
        return Type.new('None')
    return Type.new(type(node.value).__name__)


@handlers.register(astroid.JoinedStr)
def _handle_fstring(node: astroid.JoinedStr) -> Type | None:
    return Type.new('str')


@handlers.register(astroid.List)
def _handle_list(node: astroid.List) -> Type | None:
    return Type.new('list')


@handlers.register(astroid.Tuple)
def _handle_tuple(node: astroid.Tuple) -> Type | None:
    return Type.new('tuple')


@handlers.register(astroid.Dict)
def _handle_dict(node: astroid.Dict) -> Type | None:
    return Type.new('dict')


@handlers.register(astroid.Set)
def _handle_set(node: astroid.Set) -> Type | None:
    return Type.new('set')


@handlers.register(astroid.UnaryOp)
def _handle_unary_op(node: astroid.UnaryOp) -> Type | None:
    if node.op == 'not':
        return Type.new('bool')
    result = get_type(node.operand)
    if result is not None:
        result = result.add_ass(Ass.NO_UNARY_OVERLOAD)
        return result
    return None


@handlers.register(astroid.BinOp)
def _handle_binary_op(node: astroid.BinOp) -> Type | None:
    assert node.op
    lt = get_type(node.left)
    if lt is None:
        return None
    rt = get_type(node.right)
    if rt is None:
        return None
    if lt.name == rt.name == 'int':
        if node.op == '/':
            return Type.new('float')
        return lt
    if lt.name in ('float', 'int') and rt.name in ('float', 'int'):
        return Type.new('float')
    if lt.name == rt.name:
        return rt
    return None


@handlers.register(astroid.BoolOp)
def _handle_bool_op(node: astroid.BoolOp) -> Type | None:
    return Type.new('bool')


@handlers.register(astroid.Compare)
def _handle_compare(node: astroid.Compare) -> Type | None:
    if node.ops[0][0] == 'is':
        return Type.new('bool')
    return Type.new('bool', ass={Ass.NO_COMP_OVERLOAD})


@handlers.register(astroid.ListComp)
def _handle_list_comp(node: astroid.ListComp) -> Type | None:
    return Type.new('list')


@handlers.register(astroid.SetComp)
def _handle_set_comp(node: astroid.SetComp) -> Type | None:
    return Type.new('set')


@handlers.register(astroid.DictComp)
def _handle_dict_comp(node: astroid.DictComp) -> Type | None:
    return Type.new('dict')


@handlers.register(astroid.GeneratorExp)
def _handle_gen_expr(node: astroid.GeneratorExp) -> Type | None:
    return Type.new('Iterator', module='typing')


@handlers.register(astroid.Call)
def _handle_call(node: astroid.Call) -> Type | None:
    if isinstance(node.func, astroid.Attribute):
        result = _get_attr_call_type(node.func)
        if result is not None:
            return result
    if isinstance(node.func, astroid.Name):
        _, symbol_defs = node.func.lookup(node.func.name)
        mod_name = 'builtins'
        if symbol_defs:
            symbol_def = symbol_defs[0]
            if isinstance(symbol_def, astroid.ImportFrom):
                mod_name = symbol_def.modname
        result = _get_ret_type_of_fun(mod_name, node.func.name)
        if result is not None:
            return result
        if is_camel(node.func.name):
            return Type.new(node.func.name, ass={Ass.CAMEL_CASE_IS_TYPE})
    return None


@handlers.register(astroid.NodeNG)
def _handle_infer_any(node: astroid.NodeNG) -> Type | None:
    for def_node in infer(node):
        if not isinstance(def_node, astroid.Instance):
            continue
        return qname_to_type(def_node.pytype())
    return None


@handlers.register(astroid.Call)
def _handle_call_infer(node: astroid.Call) -> Type | None:
    for def_node in infer(node.func):
        if not isinstance(def_node, astroid.FunctionDef):
            continue
        mod_name, _, fun_name = def_node.qname().rpartition('.')
        return _get_ret_type_of_fun(mod_name, fun_name)
    return None


def _get_ret_type_of_fun(
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
    return _conv_node_to_type(mod_name, ret_node)


def _get_attr_call_type(node: astroid.Attribute) -> Type | None:
    expr_type = get_type(node.expr)
    if expr_type is None:
        logger.debug('cannot get type of the left side of attribute')
        return None
    module = typeshed_client.get_stub_names('builtins')
    assert module is not None
    try:
        method_def = module[expr_type.name].child_nodes[node.attrname]
    except KeyError:
        logger.debug('not a built-in function')
        return None
    if not isinstance(method_def.ast, ast.FunctionDef):
        logger.debug('resolved call target of attr is not a function')
        return None
    ret_node = method_def.ast.returns
    return _conv_node_to_type('builtins', ret_node)


def _conv_node_to_type(
    mod_name: str,
    node: ast.AST | None,
) -> Type | None:
    import builtins
    import typing

    if node is None:
        logger.debug('no return type annotation for called function def')
        return None

    # fore generics, keep it generic
    if isinstance(node, ast.Subscript):
        return _conv_node_to_type(mod_name, node.value)

    # for regular name, check if it is a typing primitive or a built-in
    if isinstance(node, ast.Name):
        name = node.id
        if hasattr(builtins, name):
            return Type.new(name, ass={Ass.NO_SHADOWING})
        if name in typing.__all__:
            return Type.new(name, module='typing')
        logger.debug(f'cannot resolve {name} into a known type')
        return None

    logger.debug('cannot resolve return AST node into a known type')
    return None
