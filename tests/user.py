import unittest
import re
import ifunny
from ifunny import objects


class UserTest(unittest.TestCase):
    user = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffirtest")

    def test_by_nick(self):
        uname = "kaffirtest"
        user = objects.User.by_nick(uname)
        assert uname == user.nick.lower()

    def test_by_nick_none(self):
        objects.User.by_nick("") == None

    def test_nick(self):
        assert self.user.nick == "kaffirtest"

    def test_repr(self):
        assert str(self.user) == "kaffirtest"

    def test_about(self):
        assert self.user.about == "I run unit tests here"

    def test_original_nick(self):
        assert isinstance(self.user.original_nick, str)

    def test_timeline_paginated(self):
        posts = self.user._timeline_paginated(limit = 1)
        assert len(posts["items"]) == 1

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

    def test_post_count(self):
        assert self.user.post_count == 8

    def test_post_count_partial(self):
        user = next(ifunny.Client().collective).author
        assert user.post_count >= 1

    def test_feature_count(self):
        assert self.user.feature_count == 0

    def test_feature_count(self):
        user = next(ifunny.Client().featured).author
        assert user.feature_count >= 1

    def test_smiles_count(self):
        assert self.user.smiles_count >= 0

    def test_smiles_count_partial(self):
        post = next(ifunny.Client().featured)
        user = post.author
        assert user.fresh.smiles_count >= post.fresh.smile_count

    def test_subscriber_count(self):
        assert self.user.subscriber_count >= 0

    def test_subscription_count(self):
        assert self.user.subscription_count >= 0

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

    def test_nick_color(self):
        regex = "[A-F0-9]{6}"
        assert re.search(regex,
                         self.user.nick_color).group() == self.user.nick_color

    def test_chat_privacy(self):
        assert self.user.chat_privacy == "public"

    def test_cover_image(self):
        assert isinstance(self.user.fresh.cover_image, objects.Image)

    def test_profile_image(self):
        assert isinstance(self.user.fresh.profile_image, objects.Image)

    def test_is_private(self):
        assert self.user.is_private == False

    def test_rating(self):
        assert isinstance(self.user.rating, objects.Rating)


if __name__ == '__main__':
    unittest.main()
