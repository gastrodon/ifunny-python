import unittest, os, json, re, random, string, time
import ifunny
from ifunny import objects
from ifunny.util import exceptions


class CommentAuthTest(unittest.TestCase):
    client = None
    post = None
    comment = None

    @classmethod
    def setUpClass(cls):
        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username, password = config["username"], config["password"]

        cls.client = ifunny.Client().login(username, password)
        cls.post = next(cls.client.timeline)
        cls.comment = next(cls.client.comments)

    @property
    def collective(self):
        feed = self.client.collective
        for _ in range(random.randrange(2, 20)):
            next(feed)
        return next(feed)

    @property
    def feature(self):
        feed = self.client.featured
        for _ in range(random.randrange(2, 20)):
            next(feed)
        return next(feed)

    def test_delete(self):
        time.sleep(10)
        comment = self.feature.add_comment("Hello, world. This is a unit test")
        comment.delete()
        assert comment.is_deleted == True

    def test_reply_text(self):
        time.sleep(10)
        text = "foobar2000"
        reply = next(self.feature.comments).reply(text)

        try:
            assert reply.content == text
        finally:
            reply.delete()

    def test_reply_post(self):
        time.sleep(10)
        t = self.client.timeline
        next(t)
        post = next(t)
        reply = next(self.feature.comments).reply("", post = post)

        try:
            assert str(reply) == post.link
        finally:
            reply.delete()

    def test_reply_post_id(self):
        time.sleep(10)
        t = self.client.timeline
        next(t)
        next(t)
        next(t)
        post = next(t)
        reply = next(self.feature.comments).reply("", post = post)

        try:
            assert str(reply) == post.link
        finally:
            reply.delete()

    def test_reply_user(self):
        time.sleep(10)
        user = self.client.user
        reply = next(self.feature.comments).reply(f"foobar {user.nick}",
                                                  user_mentions = [user])

        try:
            assert reply.user_mentions == [user]
        finally:
            reply.delete()

    def test_reply_nothing(self):
        with self.assertRaises(exceptions.NoContent):
            self.comment.reply()

    def test_reply_missing_mention_string(self):
        with self.assertRaises(exceptions.TooManyMentions):
            self.comment.reply(user_mentions = [self.client.user])

    # some tests are disabled because my testing accounts are being shadowbanned

    def _test_smile(self):
        self.comment.smile()
        assert self.comment.is_smiled == True
        self.comment.remove_smile()

    def _test_redundant_smile(self):
        self.comment.smile().smile()
        assert self.comment.is_smiled == True
        self.comment.remove_smile()

    def _test_remove_smile(self):
        self.comment.smile()
        self.comment.remove_smile()
        assert self.comment.is_smiled == False

    def _test_unsmile(self):
        self.comment.unsmile()
        assert self.comment.is_unsmiled == True
        self.comment.remove_unsmile()

    def _test_redundant_unsmile(self):
        self.comment.unsmile().unsmile()
        assert self.comment.is_unsmiled == True
        self.comments.remove_unsmile()

    def _test_remove_unsmile(self):
        self.comment.unsmile()
        self.comment.remove_unsmile()
        assert self.comment.is_unsmiled == False

    def test_report_types(self):
        valid = ["hate", "nude", "spam", "target", "harm"]

        for type in valid:
            next(self.feature.comments).report(type)

    def test_report_invalid(self):
        with self.assertRaises(TypeError):
            self.comment.report("foobar")

    def test_created_at(self):
        assert self.comment.fresh.created_at <= int(time.time())

    def test_rate_limit(self):
        with self.assertRaises(exceptions.RateLimit):
            while True:
                self.comment.reply("fast").delete()
