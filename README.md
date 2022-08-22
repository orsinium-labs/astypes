# astypes

Python library to statically detect types for AST nodes.

A good use case is a linter that needs to run some rules only for particular types. For instance, to check arguments of `something.format(a=b)` only if `something` has type `str`.

```bash
python3 -m pip install astypes
```

## Usage

Astypes uses [astroid](https://github.com/PyCQA/astroid) to infer definitions of nodes. So, if your code works with [ast](https://docs.python.org/3/library/ast.html) nodes, you'll need to convert them into astroid first:

```python
import astroid
import astypes

module = astroid.parse(source_code)
node = astypes.find_node(module, ast_node)
```

And when you have an astroid node, you can get its type:

```python
node_type = astype.get_node(node)
print(node_type.annotation)
```

Example:

```python
import astroid
import astypes

node = astroid.extract_node('1 + 2.3')
t = astypes.get_type(node)
print(t.annotation)  # 'float'
```

For a real-world usage example, check out [infer-types](https://github.com/orsinium-labs/infer-types). It is a CLI tool that automatically adds type annotations into Python code using astypes.

## How it works

You can find most of the logic in [astypes/_handlers.py](./astypes/_handlers.py). In short:

1. There are some nodes that are easy to infer type of. For example, `13` is always `int`.
1. Some nodes are also to infer, but only if to make some assumptions. Assumptions that we make are the ones that are true in 99% of cases. For example, we assume that `list(x)` returns type `list`. It might be not true if you shadow `list` with something else.
1. If the type cannot be assumed just looking at the node, we try to use [astroid](https://github.com/PyCQA/astroid) to infer the type.
1. If the returned value is a function call, we use astroid to find the definition of the function. The annotated return annotation of the function is what we need.
1. If resolved function doesn't have annotation, we use [typeshed_client](https://github.com/JelleZijlstra/typeshed_client) to get its annotation from [typeshed](https://github.com/python/typeshed). For example, for all built-in functions.
