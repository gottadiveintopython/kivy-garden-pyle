import inspect
import functools
empty = inspect.Parameter.empty


def test_freestanding_function():
    def f(a, /, b, c="C", *args, d="D", **kwargs):
        pass
    params = tuple(inspect.signature(f).parameters.values())
    assert [(p.name, p.default) for p in params] == [
        ("a", empty),
        ("b", empty),
        ("c", "C"),
        ("args", empty),
        ("d", "D"),
        ("kwargs", empty),
    ]


def test_filter_out_var_kind():
    def f(a, /, b, c="C", *args, d="D", **kwargs):
        pass
    VAR_KINDS = (
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    )
    params = tuple(inspect.signature(f).parameters.values())
    assert [(p.name, p.default) for p in params if p.kind not in VAR_KINDS] == [
        ("a", empty),
        ("b", empty),
        ("c", "C"),
        ("d", "D"),
    ]


def test_partialed_freestanding_function():
    def f(a, b, c="C"):
        pass
    f1 = functools.partial(f, "AA",)
    params = tuple(inspect.signature(f1).parameters.values())
    assert [(p.name, p.default) for p in params] == [
        ("b", empty),
        ("c", "C"),
    ]
    f2 = functools.partial(f, a="AA")
    params = tuple(inspect.signature(f2).parameters.values())
    assert [(p.name, p.default) for p in params] == [
        ("a", "AA"),
        ("b", empty),
        ("c", "C"),
    ]

def test_method():
    class MyClass:
        def f(self, a, b="B"):
            pass
    params = tuple(inspect.signature(MyClass().f).parameters.values())
    assert [(p.name, p.default) for p in params] == [
        ("a", empty),
        ("b", "B"),
    ]
    params = tuple(inspect.signature(MyClass.f).parameters.values())
    assert [(p.name, p.default) for p in params] == [
        ("self", empty),
        ("a", empty),
        ("b", "B"),
    ]


def test_bind_partial():
    def original(a, b, c="C", d="D"):
        pass
    f = functools.partial(original, "AA", d="DD")
    ba = inspect.signature(f.func).bind_partial(*f.args, **f.keywords)
    assert ba.arguments == {
        "a": "AA",
        "d": "DD",
    }
    ba.apply_defaults()
    assert ba.arguments == {
        "a": "AA",
        "c": "C",
        "d": "DD",
    }
