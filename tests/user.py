import unittest
from ifunny import objects


class UserTest(unittest.TestCase):
    user = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffirtest")  # this is my account

    def test_by_nick(self):
        uname = "kaffirtest"
        user = objects.User.by_nick(uname)
        assert isinstance(user, objects.User)
        assert uname == user.nick.lower()

    def test_timeline(self):
        post = next(self.user.timeline)
        assert isinstance(post, objects.Post)
        assert post.author == self.user

    def test_subscribers(self):
        sub = next(self.user.subscribers)
        assert isinstance(sub, objects.User)

    def test_subscriptions(self):
        sub = next(self.user.subscriptions)
        assert isinstance(sub, objects.User)

    def test_nick(self):
        assert self.user.nick == "kaffirtest"

    def test_about(self):
        assert self.user.about == "I run unit tests here"

    def test_total_posts(self):
        assert isinstance(self.user.total_posts, int)

    def test_total_featured(self):
        assert isinstance(self.user.total_featured, int)

    def test_total_smiles(self):
        assert isinstance(self.user.total_smiles, int)

    def test_subscriber_count(self):
        assert isinstance(self.user.subscriber_count, int)

    def test_subscription_count(self):
        assert isinstance(self.user.subscription_count, int)

    def test_is_verified(self):
        assert not self.user.is_verified
        assert isinstance(self.user.is_verified, bool)

    def test_is_banned(self):
        assert not self.user.is_banned
        assert isinstance(self.user.is_banned, bool)

    def test_is_deleted(self):
        assert not self.user.is_deleted
        assert isinstance(self.user.is_deleted, bool)

    def test_days(self):
        assert isinstance(self.user.days, int)

    def test_rank(self):
        assert isinstance(self.user.rank, str)

    def test_chat_privacy(self):
        assert self.user.chat_privacy == "public"

    def test_pic_url(self):
        assert isinstance(self.user.pic_url, str)
