import pytest

from kivy_garden import pyle


@pytest.fixture(scope="module")
def size_cls():
    from kivy.properties import NumericProperty
    from kivy.event import EventDispatcher

    class Size(EventDispatcher):
        width = NumericProperty()
        height = NumericProperty()
    return Size


def test_no_arg(kivy_runner, size_cls):
    from kivy_garden.pyle import throttle_rule
    af = kivy_runner.advance_frame

    area = None
    size = size_cls(width=4, height=6)

    @throttle_rule
    def keep_updating_area(dt, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        assert area is None
        af()
        assert area is None
        size.width = 2
        assert area is None
        af()
        assert area == 12
        size.height = 3
        assert area == 12
        af()
        assert area == 6

    size.width = 100
    assert area == 6
    af()
    assert area == 6

    with keep_updating_area:
        size.width = 10
        assert area == 6
    af()
    assert area == 6


@pytest.mark.parametrize("trigger_callback_on_activate", [False, True])
def test_trigger_callback_on_activate(kivy_runner, size_cls, trigger_callback_on_activate):
    from kivy_garden.pyle import throttle_rule
    af = kivy_runner.advance_frame

    area = None
    size = size_cls(width=4, height=6)

    @throttle_rule(trigger_callback_on_activate=trigger_callback_on_activate)
    def keep_updating_area(dt, s=size):
        nonlocal area
        area = s.width * s.height

    with keep_updating_area:
        assert area is None
        af()
        if trigger_callback_on_activate:
            assert area == 24
        else:
            assert area is None
        size.width = 2
        if trigger_callback_on_activate:
            assert area == 24
        else:
            assert area is None
        af()
        assert area == 12


@pytest.mark.parametrize("trigger_callback_on_activate", [False, True])
def test_reentering_should_raise_exception(kivy_runner, size_cls, trigger_callback_on_activate):
    from kivy_garden import pyle

    size = size_cls(width=4, height=6)

    @pyle.throttle_rule(trigger_callback_on_activate=trigger_callback_on_activate)
    def cm(dt, s=size):
        pass

    with cm:
        with pytest.raises(pyle.RecursiveActivationError):
            with cm:
                pass


def test_throttle_behavior(kivy_runner, size_cls):
    from kivy_garden.pyle import throttle_rule
    af = kivy_runner.advance_frame

    area = None
    size = size_cls(width=4, height=6)

    @throttle_rule(delay=1, trigger_callback_on_activate=True)
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
        assert area == 4
