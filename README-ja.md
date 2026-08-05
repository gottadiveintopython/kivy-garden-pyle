# kivy-garden-pyle

`pyle` はKv言語を用いずにPythonだけでバインディングを構築する際の手間を減らす事を目的とした実験段階のライブラリです。

例えば特定のWidgetのインスタンスに単色背景を与える機能とそれを元に戻す機能が欲しかったとします。
その実装例として次のような物が考えられます。


```python
from contextlib import ExitStack

from kivy.graphics import Color, Rectangle
from kivy.clock import Clock


def add_solid_background(widget, *, color=(1., 1. , 1., .3)):
    '''
    widgetに単色背景を与え、それを元に戻す関数を返す。
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

同等のコードを `pyle` を用いて実装するとどうなるかというと

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

このようにバインディング周りのコードがスッキリします。
またasyncライブラリを用いている場合はコルーチンの生存期間をそのまま効能期間とする、
次のような実装が良いかもしれません。

```python
from contextlib import ExitStack

import asynckivy as ak
from kivy.graphics import Color, Rectangle

from kivy_garden.pyle import throttle_rule


async def enable_solid_background(widget, *, color=(1., 1. , 1., .3)):
    '''
    コルーチンが終了するまでwidgetに単色背景を与える。
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

## そのた〜

- `throttle` と　`debounce` という語に馴染みがない人は"throttle + debounce"で検索してください。
