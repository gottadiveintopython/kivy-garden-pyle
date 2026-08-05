# kivy-garden-pyle

[日本語版](https://github.com/gottadiveintopython/kivy-garden-pyle/blob/main/README-ja.md)

`pyle` is an experimental library aimed at reducing the boilerplate needed to create Kivy bindings without using the Kv language.

For example, suppose you want a function that adds a solid-color background to a specific `Widget` instance and provides a way to revert it.
Your code might look like this:


```python
from contextlib import ExitStack

from kivy.graphics import Color, Rectangle
from kivy.clock import Clock


def add_solid_background(widget, *, color=(1., 1. , 1., .3)):
	'''
	Adds a solid-color background to widget and returns a function that reverts it.
	'''
	with ExitStack() as stack:
		defer = stack.callback

		before = widget.canvas.before
		with before:
			defer(before.remove, Color(*color))
			defer(before.remove, rect := Rectangle(pos=widget.pos, size=widget.size))

		def sync_graphics(dt, rect=rect, w=widget):
			rect.pos = w.pos
			rect.size = w.size
		t = Clock.create_trigger(sync_graphics, -1)
		defer(t.cancel)
		widget.bind(pos=t, size=t)
		defer(widget.unbind, pos=t, size=t)

		return stack.pop_all().close


revert = add_solid_background(widget)
...
revert()
```

Now, here is what an equivalent implementation looks like with `pyle`:

```python
from contextlib import ExitStack

from kivy.graphics import Color, Rectangle

from kivy_garden import pyle


def add_solid_background(widget, *, color=(1., 1. , 1., .3)):
	with ExitStack() as stack:
		defer = stack.callback

		before = widget.canvas.before
		with before:
			defer(before.remove, Color(*color))
			defer(before.remove, rect := Rectangle(pos=widget.pos, size=widget.size))

		@pyle.throttle_rule
		def sync_graphics(dt, rect=rect, w=widget):
			rect.pos = w.pos
			rect.size = w.size
		stack.enter_context(sync_graphics)

		return stack.pop_all().close
```

As you can see, the binding code becomes much cleaner.
And of course, if you are using an async library,
you may want to implement the feature as an async function,
tying the background's lifetime to the coroutine it returns:

```python
from contextlib import ExitStack

import asynckivy as ak
from kivy.graphics import Color, Rectangle

from kivy_garden import pyle


async def enable_solid_background(widget, *, color=(1., 1. , 1., .3)):
	'''
	Enables a solid-color background for a widget until the returned coroutine is cancelled.
	'''
	with ExitStack() as stack:
		defer = stack.callback

		before = widget.canvas.before
		with before:
			defer(before.remove, Color(*color))
			defer(before.remove, rect := Rectangle(pos=widget.pos, size=widget.size))

		@pyle.throttle_rule
		def sync_graphics(dt, rect=rect, w=widget):
			rect.pos = w.pos
			rect.size = w.size
		stack.enter_context(sync_graphics)

		await ak.sleep_forever()
```

In the examples above, the `@pyle.throttle_rule` decorator turns `sync_graphics` into a context manager.
At this point, bindings are not yet enabled; they are enabled only while the context manager is active.

The context manager is not reentrant, but it is reusable:

```python
# error
with sync_graphics:
    with sync_graphics:
        ...

# fine
with sync_graphics:
    ...
with sync_graphics:
    ...
```

## How does it know which Kivy properties should be observed?

It analyzes the signature and bytecode of the given function.
When the function has a pre-filled argument that is an instance of `EventDispatcher`,
any of its Kivy properties accessed via [`LOAD_ATTR`][LOAD_ATTR] will be observed.

Only the following types of "pre-filled" arguments are subjected to observation:

- default values like in the `sync_graphics` example (`w=widget`)
- values bound with `functools.partial`
- `self` arguments bound via `obj.instance_method`

Any other way of filling arguments will not create bindings.
For more details, please see [test_detect_dependencies.py][test_detect_dependencies].

## Tested on

- CPython 3.11 + Kivy 2.3.1
- CPython 3.12 + Kivy 2.3.1
- CPython 3.13 + Kivy 2.3.1
- CPython 3.14 + Kivy [`be90b9f`][be90b9f]

[test_detect_dependencies]:https://github.com/gottadiveintopython/kivy-garden-pyle/blob/main/tests/test_detect_dependencies.py
[LOAD_ATTR]:https://docs.python.org/3/library/dis.html#opcode-LOAD_ATTR
[be90b9f]:https://github.com/kivy/kivy/tree/be90b9f4bdb28c734e1cc01d6e7a7e1440e5216e
