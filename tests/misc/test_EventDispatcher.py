def test_property_method():
    from kivy.properties import StringProperty
    from kivy.event import EventDispatcher

    class Person(EventDispatcher):
        name = StringProperty()

    p = Person(name="仁科盛信")
    p.date_of_death = "15820325"
    # def property(self, name, quiet=False): ...
    assert p.property("name", True) is not None
    assert p.property("date_of_death", True) is None
