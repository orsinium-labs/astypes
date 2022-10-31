
from typing import Iterator, Tuple

import astroid

import pytest

from astypes._resolve_qualname import resolve_qualname

# from sphinx-autoapi

def generate_module_names() -> Iterator[str]:
    for i in range(1, 5):
        yield ".".join("module{}".format(j) for j in range(i))

    yield "package.repeat.repeat"


def imported_basename_cases() -> Iterator[Tuple[str, str, str]]:
    for module_name in generate_module_names():
        import_ = "import {}".format(module_name)
        basename = "{}.ImportedClass".format(module_name)
        expected = basename

        yield (import_, basename, expected)

        import_ = "import {} as aliased".format(module_name)
        basename = "aliased.ImportedClass"

        yield (import_, basename, expected)

        if "." in module_name:
            from_name, attribute = module_name.rsplit(".", 1)
            import_ = "from {} import {}".format(from_name, attribute)
            basename = "{}.ImportedClass".format(attribute)
            yield (import_, basename, expected)

            import_ += " as aliased"
            basename = "aliased.ImportedClass"
            yield (import_, basename, expected)

        import_ = "from {} import ImportedClass".format(module_name)
        basename = "ImportedClass"
        yield (import_, basename, expected)

        import_ = "from {} import ImportedClass as AliasedClass".format(module_name)
        basename = "AliasedClass"
        yield (import_, basename, expected)


def generate_args() -> Iterator[str]:
    for i in range(5):
        yield ", ".join("arg{}".format(j) for j in range(i))


def imported_call_cases() -> Iterator[Tuple[str, str, str]]:
    for args in generate_args():
        for import_, basename, expected in imported_basename_cases():
            basename += "({})".format(args)
            expected += "()"
            yield import_, basename, expected


class TestAstroidUtilsAndExpandName:

    @pytest.mark.parametrize(
        ("import_", "basename", "expected"), list(imported_basename_cases())
    )
    def test_can_get_full_imported_basename(self,
            import_:str, basename:str, expected:str) -> None:
        source = """
        {}
        class ThisClass({}): #@
            pass
        """.format(
            import_, basename
        )
        node = astroid.extract_node(source)
        basenames = resolve_qualname(node, node.basenames[0])
        assert basenames == expected

    @pytest.mark.parametrize(
        ("import_", "basename", "expected"), list(imported_call_cases())
    )
    def test_can_get_full_function_basename(self, import_:str, basename:str, expected:str) -> None:
        source = """
        {}
        class ThisClass({}): #@
            pass
        """.format(
            import_, basename
        )
        node = astroid.extract_node(source)
        basenames = resolve_qualname(node, node.basenames[0])
        assert basenames == expected