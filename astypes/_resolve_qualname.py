
from typing import  Iterable, Tuple, Union
import re

import astroid.nodes

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
def resolve_import_alias(name:str, import_names:Iterable[Tuple[str, Union[str,None]]]) -> str:
    """Resolve a name from an aliased import to its original name.
    :param name: The potentially aliased name to resolve.
    :param import_names: The pairs of original names and aliases
        from the import.
    :returns: The original name.
    """
    resolved_name = name

    for import_name, imported_as in import_names:
        if import_name == name:
            break
        if imported_as == name:
            resolved_name = import_name
            break

    return resolved_name

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
def get_full_import_name(import_from:astroid.nodes.ImportFrom, name:str) -> str:
    """Get the full path of a name from a ``from x import y`` statement.
    :param import_from: The astroid node to resolve the name of.
    :param name:
    :returns: The full import path of the name.
    """
    partial_basename = resolve_import_alias(name, import_from.names)

    module_name = import_from.modname
    if import_from.level:
        module = import_from.root()
        assert isinstance(module, astroid.nodes.Module)
        module_name = module.relative_to_absolute_name(
            import_from.modname, level=import_from.level
        )

    return "{}.{}".format(module_name, partial_basename)

# The MIT License (MIT)
# Copyright (c) 2015 Read the Docs, Inc
def resolve_qualname(
        ctx: astroid.nodes.NodeNG, 
        basename: str) -> str:
    """
    Resolve a basename to get its fully qualified name.
    :param ctx: The node representing the base name.
    :param basename: The partial base name to resolve.
    :returns: The fully resolved base name.
    """
    full_basename = basename

    top_level_name = re.sub(r"\(.*\)", "", basename).split(".", 1)[0]
    
    # re.sub(r"\(.*\)", "", basename).split(".", 1)[0]
    # Disable until pylint uses astroid 2.7
    if isinstance(
        ctx, astroid.nodes.node_classes.LookupMixIn  # pylint: disable=no-member
    ):
        lookup_node = ctx
    else:
        lookup_node = ctx.scope()

    assigns = lookup_node.lookup(top_level_name)[1]

    for assignment in assigns:
        if isinstance(assignment, astroid.nodes.ImportFrom):
            import_name = get_full_import_name(assignment, top_level_name)
            full_basename = basename.replace(top_level_name, import_name, 1)
            break
        if isinstance(assignment, astroid.nodes.Import):
            import_name = resolve_import_alias(top_level_name, assignment.names)
            full_basename = basename.replace(top_level_name, import_name, 1)
            break
        if isinstance(assignment, astroid.nodes.ClassDef):
            full_basename = assignment.qname()
            break
        if isinstance(assignment, astroid.nodes.AssignName):
            full_basename = "{}.{}".format(assignment.scope().qname(), assignment.name)

    full_basename = re.sub(r"\(.*\)", "()", full_basename)

    if full_basename.startswith("builtins."):
        return full_basename[len("builtins.") :]

    if full_basename.startswith("__builtin__."):
        return full_basename[len("__builtin__.") :]

    return full_basename