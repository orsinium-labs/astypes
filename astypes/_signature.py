"""
Module containing code to transform an astroid FunctionDef into an inspect.Sgnature object.
"""
from functools import lru_cache
import sys
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Iterator, Iterable, Tuple, Type, TypeVar, Union, cast
import itertools
import inspect
import astroid.nodes

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
def _is_ellipsis(node:astroid.nodes.NodeNG) -> bool:
    if sys.version_info < (3, 8):
        return isinstance(node, astroid.Ellipsis)

    return isinstance(node, astroid.Const) and node.value == Ellipsis #type:ignore[unreachable]

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
def _iter_args(args: List[astroid.nodes.AssignName], 
               annotations: List[astroid.nodes.AssignName], 
               defaults: List[astroid.nodes.AssignName]) -> Iterator[Tuple[str, 
                                           Optional[astroid.nodes.NodeNG], 
                                           Optional[astroid.nodes.NodeNG]]]:
    
    default_offset = len(args) - len(defaults)
    packed = itertools.zip_longest(args, annotations)
    for i, (arg, annotation) in enumerate(packed):
        default = None
        if defaults is not None and i >= default_offset:
            if defaults[i - default_offset] is not None:
                default = defaults[i - default_offset]
        name = arg.name
        yield (name, annotation, default)

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
def _merge_annotations(annotations: Iterable[Optional[astroid.nodes.NodeNG]], 
                      comment_annotations: Iterable[Optional[astroid.nodes.NodeNG]]) -> Iterator[Optional[astroid.nodes.NodeNG]]:
    for ann, comment_ann in itertools.zip_longest(annotations, comment_annotations):
        if ann and not _is_ellipsis(ann):
            yield ann
        elif comment_ann and not _is_ellipsis(comment_ann):
            yield comment_ann
        else:
            yield None

class AstValue:
    """
    Wraps an AST value inside Signature instances. 

    Formats values stored in AST expressions back to source code on calling repr().
    Used for presenting default values of parameters and annotations. 
    
    :note: The default behaviour defers to `astroid.nodes.NodeNG.as_string`. 
        This should be overriden if you want more formatting functions, like outputing HTML tags. 
    """

    def __init__(self, value: astroid.NodeNG):
        self.value = value
    def __repr__(self) -> str:
        # Since astroid do not expose the typing information yet.
        try:
            return cast(str, self.value.as_string())
        except AttributeError:
            # Can raise AttributeError from node.as_string() as not all nodes have a visitor
            return '<ERROR>'

# for the sake of type annotations
class AstParameter(inspect.Parameter):
    default: AstValue
    annotation: AstValue
class AstSignature(inspect.Signature):
    parameters: Mapping[str, inspect.Parameter]
    return_annotation: AstValue

@dataclass
class SignatureBuilder:
    """
    Builds a signature, parameter by parameter, with customizable value and signature classes.
    """
    signature_class: Type['inspect.Signature'] = field(default=inspect.Signature)
    value_class: Type['AstValue'] = field(default=AstValue)
    _parameters: List[inspect.Parameter] = field(default_factory=list, init=False)
    _return_annotation: Any = field(default=inspect.Signature.empty, init=False)

    def add_param(self, name: str, 
                  kind: inspect._ParameterKind, 
                  default: Optional[Any]=None,
                  annotation: Optional[Any]=None) -> None:
        """
        Add a new parameter to this signature.

        None values will be replaces by Parameter.empty.
        """
        default_val = inspect.Parameter.empty if default is None else self.value_class(default)
        annotation_val = inspect.Parameter.empty if annotation is None else self.value_class(annotation)
        self._parameters.append(inspect.Parameter(name, kind, default=default_val, annotation=annotation_val))

    def set_return_annotation(self, annotation: Optional[Any]) -> None:
        """
        Add a return annotation to this signature.
        """
        self._return_annotation = inspect.Signature.empty if annotation is None else self.value_class(annotation)

    def get_signature(self) -> AstSignature:
        """
        Try to create the signature object from current parameters and return it.
        :raises ValueError: If the function has invalid parameters.
        """
        return cast(AstSignature, 
            self.signature_class(self._parameters, 
            return_annotation=self._return_annotation))

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
_SignatureT = TypeVar('_SignatureT', bound=inspect.Signature)

@lru_cache
def signature(func: Union[astroid.nodes.AsyncFunctionDef, 
                            astroid.nodes.FunctionDef], 
              signature_class:Type[_SignatureT]=AstSignature, 
              value_class:Type[AstValue]=AstValue) -> _SignatureT:
    """
    Builds `inspect.Signature` representing this function's parameters and return value.

    :param func: An astroid FunctionDef.
    :param signature_class: Customizable signature class to return.
    :param value_class: Customizable value wrapper class to wrap AST values.

    :raises ValueError: If the function has invalid parameters.
    :note: does not support decorators that changes the signature. 
    """
    args_node: astroid.nodes.Arguments = func.args
    sig_builder = SignatureBuilder(signature_class=signature_class, value_class=value_class)
    positional_only_defaults: List[astroid.nodes.NodeNG] = []
    positional_or_keyword_defaults = args_node.defaults
    
    if args_node.defaults:
        args = args_node.args or []
        positional_or_keyword_defaults = args_node.defaults[-len(args) :]
        positional_only_defaults = args_node.defaults[
            : len(args_node.defaults) - len(args)
        ]

    plain_annotations = args_node.annotations or ()
    func_comment_annotations = func.type_comment_args or ()
    comment_annotations = args_node.type_comment_posonlyargs
    comment_annotations += args_node.type_comment_args or []
    comment_annotations += args_node.type_comment_kwonlyargs
    annotations = list(
        _merge_annotations(
            plain_annotations,
            _merge_annotations(func_comment_annotations, comment_annotations),
        )
    )
    annotation_offset = 0

    if args_node.posonlyargs:
        posonlyargs_annotations = args_node.posonlyargs_annotations
        if not any(args_node.posonlyargs_annotations):
            num_args = len(args_node.posonlyargs)
            posonlyargs_annotations = annotations[
                annotation_offset : annotation_offset + num_args
            ]

        for arg, annotation, default in _iter_args(
            args_node.posonlyargs, posonlyargs_annotations, positional_only_defaults
        ):
            sig_builder.add_param(arg, kind=inspect.Parameter.POSITIONAL_ONLY, 
                default=default, annotation=annotation)

        if not any(args_node.posonlyargs_annotations):
            annotation_offset += num_args

    if args_node.args:
        num_args = len(args_node.args)
        for arg, annotation, default in _iter_args(
            args_node.args,
            annotations[annotation_offset : annotation_offset + num_args],
            positional_or_keyword_defaults,
        ):
            sig_builder.add_param(arg, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                default=default, annotation=annotation)

        annotation_offset += num_args

    if args_node.vararg:
        annotation = None
        if args_node.varargannotation:
            annotation = args_node.varargannotation
        elif len(annotations) > annotation_offset and annotations[annotation_offset]:
            annotation = annotations[annotation_offset]
            annotation_offset += 1
        sig_builder.add_param(args_node.vararg, 
                kind=inspect.Parameter.VAR_POSITIONAL,
                default=None,
                annotation=annotation)

    if args_node.kwonlyargs:
        kwonlyargs_annotations = args_node.kwonlyargs_annotations
        if not any(args_node.kwonlyargs_annotations):
            num_args = len(args_node.kwonlyargs)
            kwonlyargs_annotations = annotations[
                annotation_offset : annotation_offset + num_args
            ]

        for arg, annotation, default in _iter_args(
            args_node.kwonlyargs,
            kwonlyargs_annotations,
            args_node.kw_defaults,
        ):
            sig_builder.add_param(arg, 
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=default, annotation=annotation)
            
        if not any(args_node.kwonlyargs_annotations):
            annotation_offset += num_args

    if args_node.kwarg:
        annotation = None
        if args_node.kwargannotation:
            annotation = args_node.kwargannotation
        elif len(annotations) > annotation_offset and annotations[annotation_offset]:
            annotation = annotations[annotation_offset]
            annotation_offset += 1
        sig_builder.add_param(args_node.kwarg, 
                kind=inspect.Parameter.VAR_KEYWORD,
                default=None, annotation=annotation)
    
    sig_builder.set_return_annotation(func.returns)
    return sig_builder.get_signature()