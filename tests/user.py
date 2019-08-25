import unittest
from ifunny import objects


class UserTest(unittest.TestCase):
    user = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffir")  # this is my account
        print("foo")

    def test_by_nick(self):
        uname = "kaffir"
        user = objects.User.by_nick(uname)
        assert isinstance(user, objects.User)
        assert uname == user.nick.lower()

    def test_timeline(self):
        pass
