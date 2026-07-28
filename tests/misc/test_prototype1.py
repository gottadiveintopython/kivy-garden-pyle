import types
import inspect
import dis

opmap = dis.opmap


def detect_dependencies(
    func,
    empty=inspect.Parameter.empty,
    LOAD_ATTR=opmap["LOAD_ATTR"],
    LOAD_FASTs=(opmap["LOAD_FAST"], opmap.get("LOAD_FAST_BORROW")),
    LOAD_FAST_2xs=(opmap.get("LOAD_FAST_LOAD_FAST"), opmap.get("LOAD_FAST_BORROW_LOAD_FAST_BORROW")),
) -> list[tuple]:
    get_target = {
        name: default
        for name, p in inspect.signature(func).parameters.items()
        if (default := p.default) is not empty and isinstance(default, types.SimpleNamespace)
    }.get
    dependencies = []
    inst_iter = dis.get_instructions(func)
    for inst in inst_iter:
        if inst.opcode in LOAD_FASTs and (target := get_target(inst.argval)) is not None:
            pass
        elif inst.opcode in LOAD_FAST_2xs and (target := get_target(inst.argval[1])) is not None:
            pass
        else:
            continue
        inst2 = next(inst_iter)
        if inst2.opcode != LOAD_ATTR:
            continue
        dependencies.append((target, inst2.argval))
    return dependencies


def test_irrelevant_assignments_1():
    def f(irrel, rel=types.SimpleNamespace()):
        irrel = rel
        irrel = irrel
        irrel = irrel.val

        irrel.val = rel
        irrel.val = irrel
        irrel.val = irrel.val

        rel = rel
        rel = irrel
        rel = irrel.val

        rel.val = rel
        rel.val = irrel
        rel.val = irrel.val
    assert detect_dependencies(f) == []


def test_irrelevant_assignments_2():
    def f(rel=types.SimpleNamespace(), irrel="Hello"):
        irrel = rel
        irrel = irrel
        irrel = irrel.val

        irrel.val = rel
        irrel.val = irrel
        irrel.val = irrel.val

        rel = rel
        rel = irrel
        rel = irrel.val

        rel.val = rel
        rel.val = irrel
        rel.val = irrel.val
    assert detect_dependencies(f) == []


def test_relevant_assignments_1():
    rel = types.SimpleNamespace()

    def f(rel=rel, irrel="Hello"):
        irrel = rel.val1
        irrel.val2 = rel.val3
        rel = rel.val4
        rel.val5 = rel.val6
    assert detect_dependencies(f) == [
        (rel, "val1"),
        (rel, "val3"),
        (rel, "val4"),
        (rel, "val6"),
    ]


def test_relevant_assignments_2():
    rel = types.SimpleNamespace()

    def f(irrel, rel=rel):
        irrel = rel.val1
        irrel.val2 = rel.val3
        rel = rel.val4
        rel.val5 = rel.val6
    assert detect_dependencies(f) == [
        (rel, "val1"),
        (rel, "val3"),
        (rel, "val4"),
        (rel, "val6"),
    ]


def test_relevant_call():
    rel = types.SimpleNamespace()

    def f(irrel, rel=rel):
        max(rel.val1, rel.val2)
    assert detect_dependencies(f) == [
        (rel, "val1"),
        (rel, "val2"),
    ]


def test_partially_relevant_call():
    rel = types.SimpleNamespace()

    def f(irrel, rel=rel):
        max(rel.val1, irrel)
        max(irrel, rel.val2)
    assert detect_dependencies(f) == [
        (rel, "val1"),
        (rel, "val2"),
    ]
