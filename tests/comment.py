import unittest
from ifunny import objects


class CommentTest(unittest.TestCase):
    user = None
    comment = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffirtest")
        cls.comment = next(next(user.timeline).comments)
