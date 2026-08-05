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

このようにバインディング周りのコードがスッキリします。
またasyncライブラリを用いている場合はasync関数として実装してコルーチンの生存期間をそのまま効能期間とする、
次のような実装が良いかもしれません。

```python
from contextlib import ExitStack

import asynckivy as ak
from kivy.graphics import Color, Rectangle

from kivy_garden import pyle


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

        @pyle.throttle_rule
        def sync_graphics(dt, rect=rect, w=widget):
            rect.pos = w.pos
            rect.size = w.size
        stack.enter_context(sync_graphics)

        await ak.sleep_forever()
```

上記の例らにおける `sync_graphics` 関数は `@pyle.throttle_rule` で飾られた事によってコンテキストマネージャー(長いので以後はcmと略す)と化します。
このcmが作られた段階ではまだバインディングは有効になっておらず、活動中(`__enter__`から`__exit__`まで)のみ有効になります。
このcmは再帰的に`__enter__`できませんが再利用は可能です。

```python
# 再帰は駄目
with sync_graphics:
    with sync_graphics:
        ...

# 再利用は構わない
with sync_graphics:
    ...
with sync_graphics:
    ...
```

## どのようにして監視すべきKivyプロパティを検出するのか

関数のバイトコードを解析しています。
関数の **あらかじめ埋められた** 引数に`EventDispatcher`のインスタンスがある時、
それに対するKivyプロパティの読み出し([LOAD_ATTR][LOAD_ATTR])があるとそれを監視対象とします。

対応している "あらかじめ埋められた" 引数は以下の三種のみです。

- `sync_graphics` の例のようなデフォルト引数(`w=widget`)
- `functools.partial` で埋められた値
- `obj.instance_method` で結び付けられた `self` 引数

それ以外のやり方で引数を埋めても監視対象にはなりません。
より詳しくは[test_detect_dependencies.py][test_detect_dependencies]を参照してください。

## そのた〜

- `throttle` と　`debounce` という語に馴染みがない人は"throttle + debounce"で検索してください。


[test_detect_dependencies]:https://github.com/gottadiveintopython/kivy-garden-pyle/blob/main/tests/test_detect_dependencies.py
[LOAD_ATTR]:https://docs.python.org/3/library/dis.html#opcode-LOAD_ATTR
