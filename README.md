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

For a real-world usage example, check out [infer-types](https://github.com/orsinium-labs/infer-types). It is a CLI tool that automatically adds type annotations into Python code using astypes.
