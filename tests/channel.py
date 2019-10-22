import unittest
from ifunny import objects


class ChannelTest(unittest.TestCase):
    user = None
    channels = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects._mixin.ClientBase()
        cls.channels = cls.user.channels

    def test_channel(self):
        assert isinstance(self.channels[0], objects.Channel)

    def test_feed(self):
        for channel in self.channels:
            assert isinstance(next(channel.feed), objects.Post)


if __name__ == '__main__':
    unittest.main()
