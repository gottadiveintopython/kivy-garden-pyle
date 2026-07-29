import pytest
from kivy_garden.pyle import detect_dependencies


@pytest.fixture(scope="module")
def person_cls():
    from kivy.properties import NumericProperty, ObjectProperty, StringProperty
    from kivy.event import EventDispatcher

    class Person(EventDispatcher):
        name = StringProperty()
        age = NumericProperty()
        parent = ObjectProperty(None, allownone=True)

        def greet(self, child=None):
            return f"Hello, I'm {self.name} and am {self.age} years old. I have a child named {child.name}."

    return Person


@pytest.fixture()
def person(person_cls):
    return person_cls(age=30)


def test_non_EventDispatcher_should_be_ignored():
    import types
    def f(v=types.SimpleNamespace(age=30)):
        max(v, v)
        max(v.age, v.age)
        v.age = v.age
    assert detect_dependencies(f) == []


def test_deep_attribute_lookup_should_be_ignored(person_cls):
    alice = person_cls()
    bob = person_cls(parent=alice)

    def f(alice=alice, bob=bob):
        print(bob.parent.age)
    assert detect_dependencies(f) == [
        (bob, "parent"),
    ]


def test_regular_python_attributes_should_be_ignored(person):
    person.attr = None

    def f(p=person):
        max(p.attr, p.attr)
        p.attr = p.attr
    assert detect_dependencies(f) == []


def test_attribute_lookups_on_non_function_parameters_should_be_ignored(person):
    def f(p=person):
        p2 = p
        max(p2.name, person.age)
    assert detect_dependencies(f) == []


def test_function_arguments(person):
    def f(p=person):
        print(p.name, p.age)
    assert detect_dependencies(f) == [
        (person, "name"),
        (person, "age"),
    ]


def test_fstring(person):
    def f(p=person):
        return f"{p.name}, {p.age}"
    assert detect_dependencies(f) == [
        (person, "name"),
        (person, "age"),
    ]


def test_duplications(person):
    def f(p=person):
        print(p.name, p.name)
    assert detect_dependencies(f) == [
        (person, "name"),
    ]


def test_STORE_ATTR_should_be_ignored(person):
    def f(p=person):
        p.name = p.parent
    assert detect_dependencies(f) == [
        (person, "parent"),
    ]


def test_functools_partial(person_cls):
    from functools import partial

    alice = person_cls()
    bob = person_cls()
    clare = person_cls()

    def f(p1, p2=clare, p3=clare):
        print(p1.name, p2.age, p3.parent)
    assert detect_dependencies(partial(f, alice, p3=bob)) == [
        (alice, "name"),
        (clare, "age"),
        (bob, "parent"),
    ]


def test_bound_method(person):
    assert detect_dependencies(person.greet) == [
        (person, "name"),
        (person, "age"),
    ]


def test_functools_partial_combined_with_bound_method(person_cls):
    from functools import partial

    alice = person_cls()
    bob = person_cls()
    assert detect_dependencies(partial(alice.greet, bob)) == [
        (alice, "name"),
        (alice, "age"),
        (bob, "name"),
    ]
