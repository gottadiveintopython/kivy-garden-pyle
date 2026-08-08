__all__ = (
    "RecursiveActivationError",
    "immediate_rule", "throttle_rule", "debounce_rule",
)

from collections.abc import Callable
import types
from inspect import signature
from dis import opmap, get_instructions
from functools import partial

from kivy._event import EventDispatcher
from kivy.clock import Clock


class RecursiveActivationError(Exception):
    '''
    Raised when a rule is recursively activated.

    .. code-block::

        from kivy_garden import pyle

        @pyle.immediate_rule
        def xxx(...):
            ...

        with xxx:
            with xxx:  # raises RecursiveActivationError
                ...
    '''


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


class RuleBase:
    def __init__(self, trigger_callback_on_activate, original_callback, direct_callback=None):
        self.trigger_callback_on_activate = trigger_callback_on_activate
        self.__callback = direct_callback or original_callback
        self.__deps = detect_dependencies(original_callback)
        self.__unbind_uids = None
        self.__active = False

    def __enter__(self):
        if self.__active:
            raise RecursiveActivationError
        cb = self.__callback
        self.__unbind_uids = [owner.fbind(prop_name, cb) for owner, prop_name in self.__deps]
        self.__active = True
        if self.trigger_callback_on_activate:
            cb(None, None)

    def __exit__(self, *args):
        assert self.__active
        for (owner, prop_name), uid in zip(self.__deps, self.__unbind_uids):
            owner.unbind_uid(prop_name, uid)
        self.__active = False

    def add_dependency(self, owner: EventDispatcher, prop_or_event: str):
        dep = (owner, prop_or_event)
        if dep in self.__deps:
            return
        self.__deps.append(dep)
        if self.__active:
            self.__unbind_uids.append(owner.fbind(prop_or_event, self.__callback))

    def remove_dependency(self, owner: EventDispatcher, prop_or_event: str):
        dep = (owner, prop_or_event)
        deps = self.__deps
        if dep not in deps:
            return
        if self.__active:
            idx = deps.index(dep)
            deps.pop(idx)
            owner.unbind_uid(prop_or_event, self.__unbind_uids.pop(idx))
        else:
            deps.remove(dep)


def immediate_rule(callback=None, *, trigger_callback_on_activate=False):
    if callback is None:
        return partial(RuleBase, trigger_callback_on_activate)
    else:
        return RuleBase(trigger_callback_on_activate, callback)


def throttle_rule(callback=None, *, trigger_callback_on_activate=False, delay=-1):
    if callback is None:
        return partial(ThrottleRule, delay, trigger_callback_on_activate)
    else:
        return ThrottleRule(delay, trigger_callback_on_activate, callback)


class ThrottleRule(RuleBase):
    def __init__(self, delay, trigger_callback_on_activate, callback):
        self._trigger = t = Clock.create_trigger(callback, delay)
        super().__init__(trigger_callback_on_activate, callback, t)

    def __exit__(self, *args):
        self._trigger.cancel()
        return super().__exit__(*args)


def debounce_rule(callback=None, *, trigger_callback_on_activate=False, delay=1):
    if callback is None:
        return partial(DebounceRule, delay, trigger_callback_on_activate)
    else:
        return DebounceRule(delay, trigger_callback_on_activate, callback)


def _restart_trigger(trigger, *args):
    trigger.cancel()
    trigger()


class DebounceRule(RuleBase):
    def __init__(self, delay, trigger_callback_on_activate, callback):
        self._trigger = t = Clock.create_trigger(callback, delay)
        super().__init__(trigger_callback_on_activate, callback, partial(_restart_trigger, t))

    def __exit__(self, *args):
        self._trigger.cancel()
        return super().__exit__(*args)
