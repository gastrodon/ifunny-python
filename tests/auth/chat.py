import unittest, json, os, requests, re, time
from ifunny import Client, objects, ext
from ifunny.util import exceptions


class ChatTestAuth(unittest.TestCase):
    client = None

    @classmethod
    def setUpClass(cls):
        cls.ts = int(time.time())
        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username, password = config["username"], config["password"]

        cls.client = Client().login(username, password)
