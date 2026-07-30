__all__ = (
    "immediate_reaction", "throttle_reaction", "debounce_reaction",
    "immediate_rule", "throttle_rule", "debounce_rule",
)

from collections.abc import Callable
import types
from inspect import signature
from dis import opmap, get_instructions
from functools import partial

from kivy._event import EventDispatcher
from kivy.clock import Clock


def _is_event_dispatcher(obj, _hasattr=hasattr) -> bool:
    return _hasattr(obj, "fbind")


def detect_dependencies(
    f: Callable,
    override_params=types.MappingProxyType({}),
    LOAD_ATTR=opmap["LOAD_ATTR"],
    LOAD_FASTs=(opmap["LOAD_FAST"], opmap.get("LOAD_FAST_BORROW")),
    LOAD_FAST_2xs=(opmap.get("LOAD_FAST_LOAD_FAST"), opmap.get("LOAD_FAST_BORROW_LOAD_FAST_BORROW")),
) -> list[tuple[EventDispatcher, str]]:
    '''
    (internal)
    Analyzes a function's bytecode to detect the Kivy properties it depends on.

    .. code-block::

        widget = Widget()

        def f(w=widget, nspace=types.SimpleNamespace(...)):
            print(w.x, nspace.foo)
            w.width = w.height

        assert detect_dependencies(f) == [
            (widget, "x"), (widget, "height"),
        ]

    Unlike the Kv language, detection is very limited:

    .. code-block::

        widget = Widget()

        def f(w=widget):
            # 'widget.width' isn't detected because 'widget' is not a function parameter's name.
            print(widget.width)

            # Deep attribute lookup is not supported so only 'w.parent' is detected but 'w.parent.x' isn't.
            print(w.parent.x)

            # 'w.height' is INCORRECTLY detected.
            w = another_widget
            print(w.height)

        assert detect_dependencies(f) == [
            (widget, "parent"), (widget, "height"),
        ]
    '''
    if isinstance(f, partial):  # `functools.partial` ?
        additional_params = signature(f.func).bind_partial(*f.args, **f.keywords).arguments
        return detect_dependencies(f.func, {**additional_params, **override_params})
    if hasattr(f, "__self__"):  # bound method ?
        first_param_name = next(iter(signature(f.__func__).parameters))
        return detect_dependencies(f.__func__, {**override_params, first_param_name: f.__self__})

    is_event_dispatcher = _is_event_dispatcher
    owners = {
        name: default
        for name, p in signature(f).parameters.items()
        if is_event_dispatcher(default := p.default)
    }
    owners.update(
        (k, v) for k, v in override_params.items()
        if is_event_dispatcher(v)
    )

    dependencies = []
    next_ = next
    add_dependency = dependencies.append
    get_owner = owners.get
    inst_iter = get_instructions(f)
    for inst in inst_iter:
        if inst.opcode in LOAD_FASTs and (owner := get_owner(inst.argval)) is not None:
            pass
        elif inst.opcode in LOAD_FAST_2xs and (owner := get_owner(inst.argval[1])) is not None:
            pass
        else:
            continue
        inst2 = next_(inst_iter)
        if inst2.opcode != LOAD_ATTR:
            continue
        attr_name = inst2.argval
        # def property(self, name, quiet=False):
        if owner.property(attr_name, True) is None:
            continue
        dep = (owner, attr_name)
        if dep not in dependencies:
            add_dependency(dep)
    return dependencies


def immediate_reaction(callback=None, *, react_on_activate=False):
    if callback is None:
        return partial(ImmediateReaction, react_on_activate)
    else:
        return ImmediateReaction(react_on_activate, callback)


class ImmediateReaction:
    def __init__(self, react_on_activate, callback):
        self._callback = callback
        self.react_on_activate = react_on_activate
        self._deps = detect_dependencies(callback)
        self._unbind_uids = None
        self._active = False

    def __enter__(self):
        if self._active:
            raise Exception("The rule is already active.")
        cb = self._callback
        self._unbind_uids = [owner.fbind(prop_name, cb) for owner, prop_name in self._deps]
        self._active = True
        if self.react_on_activate:
            cb(None, None)

    def __exit__(self, *args):
        if not self._active:
            raise Exception("The rule is not active.")
        for (owner, prop_name), uid in zip(self._deps, self._unbind_uids):
            owner.unbind_uid(prop_name, uid)
        self._active = False


def throttle_reaction(callback=None, *, react_on_activate=True, delay=-1):
    if callback is None:
        return partial(ThrottleReaction, delay, react_on_activate)
    else:
        return ThrottleReaction(delay, react_on_activate, callback)


class ThrottleReaction:
    def __init__(self, delay, react_on_activate, callback):
        self.react_on_activate = react_on_activate
        self._deps = detect_dependencies(callback)
        self._unbind_uids = None
        self._active = False
        self._trigger = Clock.create_trigger(callback, delay)

    def __enter__(self):
        if self._active:
            raise Exception("The rule is already active.")
        t = self._trigger
        self._unbind_uids = [owner.fbind(prop_name, t) for owner, prop_name in self._deps]
        self._active = True
        if self.react_on_activate:
            t()

    def __exit__(self, *args):
        if not self._active:
            raise Exception("The rule is not active.")
        for (owner, prop_name), uid in zip(self._deps, self._unbind_uids):
            owner.unbind_uid(prop_name, uid)
        self._trigger.cancel()
        self._active = False


def debounce_reaction(callback=None, *, react_on_activate=True, delay=1):
    if callback is None:
        return partial(DebounceReaction, delay, react_on_activate)
    else:
        return DebounceReaction(delay, react_on_activate, callback)


class DebounceReaction:
    def __init__(self, delay, react_on_activate, callback):
        self.react_on_activate = react_on_activate
        self._deps = detect_dependencies(callback)
        self._unbind_uids = None
        self._active = False
        self._trigger = t = Clock.create_trigger(callback, delay)
        self._wrapper = partial(self._wrapper, t)

    def __enter__(self):
        if self._active:
            raise Exception("The rule is already active.")
        f = self._wrapper
        self._unbind_uids = [owner.fbind(prop_name, f) for owner, prop_name in self._deps]
        self._active = True
        if self.react_on_activate:
            f()

    def __exit__(self, *args):
        if not self._active:
            raise Exception("The rule is not active.")
        for (owner, prop_name), uid in zip(self._deps, self._unbind_uids):
            owner.unbind_uid(prop_name, uid)
        self._trigger.cancel()
        self._active = False

    @staticmethod
    def _wrapper(trigger, *args):
        trigger.cancel()
        trigger()


immediate_rule = immediate_reaction
throttle_rule = throttle_reaction
debounce_rule = debounce_reaction
