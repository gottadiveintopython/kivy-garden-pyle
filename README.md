# kivy-garden-pyle

`pyle` is an experimental library aimed at reducing the boilerplate needed to create Kivy bindings without using the Kv language.

For example, suppose you want a function that adds a solid-color background to a specific `Widget` instance as well as a way to reverts it.
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

from kivy_garden.pyle import throttle_rule


def add_solid_background(widget, *, color=(1., 1. , 1., .3)):
	with ExitStack() as stack:
		defer = stack.callback

		before = widget.canvas.before
		with before:
			defer(before.remove, Color(*color))
			defer(before.remove, rect := Rectangle(pos=widget.pos, size=widget.size))

		@throttle_rule
		def sync_graphics(dt, rect=rect, w=widget):
			rect.pos = w.pos
			rect.size = w.size
		stack.enter_context(sync_graphics)

		return stack.pop_all().close
```

As you can see, the binding code became much cleaner.
And of course, if you are using an async library,
you may want to tie the background's lifetime to that of the coroutine:

```python
from contextlib import ExitStack

import asynckivy as ak
from kivy.graphics import Color, Rectangle

from kivy_garden.pyle import throttle_rule


async def enable_solid_background(widget, *, color=(1., 1. , 1., .3)):
	'''
	Adds a solid-color background to a widget until the returned coroutine is cancelled.
	'''
	with ExitStack() as stack:
		defer = stack.callback

		before = widget.canvas.before
		with before:
			defer(before.remove, Color(*color))
			defer(before.remove, rect := Rectangle(pos=widget.pos, size=widget.size))

		@throttle_rule
		def sync_graphics(dt, rect=rect, w=widget):
			rect.pos = w.pos
			rect.size = w.size
		stack.enter_context(sync_graphics)

		await ak.sleep_forever()
```
