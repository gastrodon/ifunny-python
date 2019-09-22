import unittest, os, json, re, random, string, time
import ifunny
from ifunny import objects
from ifunny.util import exceptions


class PostAuthTest(unittest.TestCase):
    image_png = "https://safebooru.org//images/2782/308d1f35ff658731d3ade7f5b49673a85f5a6dc9.png"
    client = None
    post = None

    @classmethod
    def setUpClass(cls):
        cls.ts = int(time.time())
        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username, password = config["username"], config["password"]

        cls.client = Client().login(username, password)
        cls.post = next(cls.client.timeline)

    @property
    def new_post(self):
        return self.client.post_image_url(self.image_png, wait = True)
