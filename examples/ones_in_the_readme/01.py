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


def main():
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.animation import Animation
    from kivy.uix.widget import Widget
    from kivy.uix.label import Label

    class TestApp(App):
        def build(self):
            root = Widget()
            root.add_widget(Label(font_size=80, text="A"))
            return root

        def on_start(self):
            root = self.root
            target = root.children[0]
            anim = Animation(right=root.width, height=root.height) + Animation(x=0, height=100)
            anim.repeat = True
            anim.start(target)
            revert = add_solid_background(target)
            Clock.schedule_once(lambda dt: revert(), 4)

    TestApp().run()


if __name__ == "__main__":
    main()
