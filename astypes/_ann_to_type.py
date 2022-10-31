"""
Adjusted from griffe/src/griffe/agents/nodes.py
"""

import sys
import typing as t
import astroid

from ._type import Type, union
from ._signature import AstValue
from ._resolve_qualname import resolve_qualname

def node2dottedname(node: t.Optional[astroid.nodes.NodeNG]) -> t.Optional[t.List[str]]:
    """
    Resove expression composed by `astroid.nodes.Attribute` and `astroid.nodes.Name` nodes to a list of names. 
    :note: Supports variants `AssignAttr` and `AssignName`.
    """
    parts = []
    while isinstance(node, (astroid.nodes.Attribute, astroid.nodes.AssignAttr)):
        parts.append(node.attrname or '')
        node = node.expr
    if isinstance(node, (astroid.nodes.Name, astroid.nodes.AssignName)):
        parts.append(node.name or '')
    else:
        return None
    parts.reverse()
    return parts

def node2qualname(node: t.Optional[astroid.nodes.NodeNG]) -> t.Optional[str]:
    """
    Resove expression composed by `Attribute` and `Name` nodes to a fuller name
    """
    dottedname = node2dottedname(node)
    if dottedname:
        return resolve_qualname(node, '.'.join(dottedname))
    return None

# ==========================================================
# annotations
def _get_attribute_annotation(node: astroid.Attribute) -> Type:
    qualname = node2qualname(node)
    if qualname:
        module, _, name = qualname.rpartition('.')
        return Type.new(name, module=module)
    else:
        # the annotation is something like func().Something, not an actual name.
        return Type.new(node.attrname, module=repr(AstValue(node.expr)))

def _get_binop_annotation(node: astroid.BinOp) -> Type:
    # support new style unions
    if node.op == '|':
        left = get_annotation(node.left)
        right = get_annotation(node.right)
        return union(left, right)
    else:
        raise KeyError(node.op)

def _get_constant_annotation(node: astroid.Const) -> Type | None: 
    # TODO unstring annotation before.   
    return _get_literal_annotation(node)

def _get_ellipsis_annotation(node: astroid.Ellipsis) -> Type:
    return Type.new('...') 

def _get_literal_annotation(node: astroid.Const) -> str:
    # special case Ellipsis
    name = {type(...): lambda _: "..."}.get(type(node.value), repr)(node.value)
    return Type.new(name)

# Sometimes, software abuse annotations for other stuff, new don't recognize this
# def _get_keyword_annotation(node: astroid.Keyword) -> Type:
#     return Type(f"{node.arg}=", get_annotation(node.value))

# List annotation is used for Callables
# def _get_list_annotation(node: astroid.List) -> Type:
#     return Type("[", *_join([get_annotation(el) for el in node.elts], ", "), "]")


def _get_name_annotation(node: astroid.Name) -> Type:
    qualname = node2qualname(node)
    if qualname:
        module, _, name = qualname.rpartition('.')
        return Type.new(name, module=module)
    else:
        return Type(node.name)


def _get_subscript_annotation(node: astroid.Subscript) -> Type:
    left = get_annotation(node.value)
    if isinstance(node.slice, astroid.Tuple):
        args = _get_tuple_annotation(node.slice)
        left = left.replace(args=args)
        # _node_annotation_map[astroid.Const] = _get_literal_annotation
        # subscript = get_annotation(node.slice)
        # _node_annotation_map[astroid.Const] = _get_constant_annotation
    else:
        arg = get_annotation(node.slice)
        if arg:
            left = left.replace(args=[arg])    
    return left

def _get_tuple_annotation(node: astroid.Tuple) -> t.List[Type]:
    return [get_annotation(el) or Type.new('') for el in node.elts]


# def _get_unaryop_annotation(node: astroid.UnaryOp) -> Type:
#     return Type(get_annotation(node.op), get_annotation(node.operand))


# def _get_uadd_annotation(node: astroid.UAdd) -> str:
#     return "+"


# def _get_usub_annotation(node: astroid.USub) -> str:
#     return "-"


_node_annotation_map: dict[Type, t.Callable[[t.Any], Type]] = {
    astroid.Attribute: _get_attribute_annotation,
    astroid.BinOp: _get_binop_annotation,
    astroid.Const: _get_constant_annotation,
    # astroid.IfExp: _get_ifexp_annotation,
    # astroid.Invert: _get_invert_annotation,
    # astroid.Keyword: _get_keyword_annotation,
    # astroid.List: _get_list_annotation,
    astroid.Name: _get_name_annotation,
    astroid.Subscript: _get_subscript_annotation,
    astroid.Tuple: _get_tuple_annotation,
    # astroid.UnaryOp: _get_unaryop_annotation,
    # astroid.UAdd: _get_uadd_annotation,
    # astroid.USub: _get_usub_annotation,
}

if sys.version_info < (3, 8):
    _node_annotation_map[astroid.Ellipsis] = _get_ellipsis_annotation

def _get_annotation(node: astroid.NodeNG) -> Type:
    return _node_annotation_map[type(node)](node)


def get_annotation(node: astroid.NodeNG | None) -> Type:
    """Extract a resolvable annotation.
    Parameters:
        node: The annotation node.
    Returns:
        A Type instance. Returns the unknown type if we can't make sens of the type annotation.
    """

    try:
        return _get_annotation(node)
    except KeyError:
        return Type.new('')