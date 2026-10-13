import pytest


@pytest.fixture(scope="module")
def size_cls():
    from kivy.properties import NumericProperty
    from kivy.event import EventDispatcher

    class Size(EventDispatcher):
        width = NumericProperty()
        height = NumericProperty()
    return Size


def test_no_arg(kivy_runner, size_cls):
    from kivy_garden.pyle import debounce_rule
    af = kivy_runner.advance_frame

    area = None
    size = size_cls(width=4, height=6)

    @debounce_rule
    def keep_updating_area(dt, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        assert area is None
        af(dt=2)
        assert area is None
        size.width = 2
        assert area is None
        af(dt=2)
        assert area == 12
        size.height = 3
        assert area == 12
        af(dt=2)
        assert area == 6

    size.width = 100
    assert area == 6
    af(dt=2)
    assert area == 6

    with keep_updating_area:
        size.width = 10
        assert area == 6
    af(dt=2)
    assert area == 6


@pytest.mark.parametrize("eager", [False, True])
def test_eager(kivy_runner, size_cls, eager):
    from kivy_garden.pyle import debounce_rule
    af = kivy_runner.advance_frame

    area = None
    size = size_cls(width=4, height=6)

    @debounce_rule(eager=eager)
    def keep_updating_area(dt, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        assert area is None
        af(dt=2)
        if eager:
            assert area == 24
        else:
            assert area is None
        size.width = 2
        if eager:
            assert area == 24
        else:
            assert area is None
        af(dt=2)
        assert area == 12


@pytest.mark.parametrize("eager", [False, True])
def test_reentering_should_raise_exception(kivy_runner, size_cls, eager):
    from kivy_garden import pyle

    size = size_cls(width=4, height=6)

    @pyle.debounce_rule(eager=eager)
    def cm(dt, s=size):
        pass

    with cm:
        with pytest.raises(pyle.RecursiveActivationError):
            with cm:
                pass


def test_debounce_behavior(kivy_runner, size_cls):
    from kivy_garden.pyle import debounce_rule
    af = kivy_runner.advance_frame

    area = None
    size = size_cls(width=4, height=6)

    @debounce_rule(delay=1, eager=True)
    def keep_updating_area(dt, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        assert area is None
        af(dt=0.7)
        assert area is None
        af(dt=0.7)
        assert area == 24
        size.height = 3
        assert area == 24
        af(dt=0.7)
        assert area == 24
        size.height = 1
        assert area == 24
        af(dt=0.7)
        assert area == 24
        af(dt=0.7)
        assert area == 4
