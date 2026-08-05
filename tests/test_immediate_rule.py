import pytest


@pytest.fixture(scope="module")
def size_cls():
    from kivy.properties import NumericProperty
    from kivy.event import EventDispatcher

    class Size(EventDispatcher):
        width = NumericProperty()
        height = NumericProperty()
    return Size


def test_no_arg(size_cls):
    from kivy_garden.pyle import immediate_rule

    area = None
    size = size_cls(width=4, height=6)

    @immediate_rule
    def keep_updating_area(_1, _2, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        assert area is None
        size.width = 2
        assert area == 12
        size.height = 3
        assert area == 6

    size.width = 100
    assert area == 6

    with keep_updating_area:
        assert area == 6


@pytest.mark.parametrize("react_on_activate", [False, True])
def test_react_on_activate(size_cls, react_on_activate):
    from kivy_garden.pyle import immediate_rule

    area = None
    size = size_cls(width=4, height=6)

    @immediate_rule(react_on_activate=react_on_activate)
    def keep_updating_area(_1, _2, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        if react_on_activate:
            assert area == 24
        else:
            assert area is None
        size.width = 2
        assert area == 12
        size.height = 3
        assert area == 6

    size.width = 100
    assert area == 6

    with keep_updating_area:
        if react_on_activate:
            assert area == 300
        else:
            assert area == 6


@pytest.mark.parametrize("react_on_activate", [False, True])
def test_reentering_should_raise_exception(size_cls, react_on_activate):
    from kivy_garden.pyle import immediate_rule

    size = size_cls(width=4, height=6)

    @immediate_rule(react_on_activate=react_on_activate)
    def cm(_1, _2, s=size):
        pass

    with cm:
        with pytest.raises(Exception):
            with cm:
                pass
