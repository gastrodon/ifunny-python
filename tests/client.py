import unittest, json, os, requests
from ifunny import Client, ext


class ClientTest(unittest.TestCase):
    client = None

    @classmethod
    def setUpClass(cls):
        cls.client = Client()

    def test_create_command(self):
        @self.client.command()
        def foo():
            return

        assert isinstance(self.client.commands["foo"], ext.commands.Command)

    def test_create_named_command(self):
        @self.client.command(name = "bar")
        def foo():
            return

        assert isinstance(self.client.commands["bar"], ext.commands.Command)

    def test_prefix_default(self):
        assert Client().prefix == {""}

    def test_prefix_string(self):
        assert Client(prefix = "foo").prefix == {"foo"}

    def test_prefix_list(self):
        assert Client(prefix = ["foo", "bar"]).prefix == {"foo", "bar"}

    def test_prefix_tuple(self):
        assert Client(prefix = ("foo", "bar")).prefix == {"foo", "bar"}

    def test_prefix_function(self):
        def foo():
            return "bar"

        assert Client(prefix = foo).prefix == {"bar"}

    def test_prefix_lambda(self):
        foo = lambda: "bar"

        assert Client(prefix = foo).prefix == {"bar"}
