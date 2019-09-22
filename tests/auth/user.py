import unittest, os, json, re, random, string
import ifunny
from ifunny import objects
from ifunny.util import exceptions


class UserAuthTest(unittest.TestCase):
    client = None
    kaffir = None

    @property
    def user(self):
        return next(self.client.collective).author

    @classmethod
    def setUpClass(cls):
        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username, password = config["username"], config["password"]

        cls.client = ifunny.Client().login(username, password)
        cls.kaffir = ifunny.objects.User.by_nick("kaffir", client = cls.client)

    def test_is_subscribed(self):
        assert self.kaffir.is_subscribed == True

    def test_is_subscription(self):
        assert self.kaffir.is_subscription == True

    def test_is_updates_subscription(self):
        assert self.kaffir.is_updates_subscription == True

    def test_can_chat(self):
        assert self.kaffir.can_chat == True

    def test_blocking_me(self):
        user = objects.User.by_nick("removeddit", client = self.client)
        assert user.blocking_me == True

    def test_is_blocked(self):
        user = objects.User.by_nick("removeddit", client = self.client)
        assert user.is_blocked == True

    def test_chat_url(self):
        url = self.kaffir.chat_url
        assert re.compile("sendbird_group_channel_[0-9]+_[0-9a-f]+").match(url)

    def test_chat(self):
        assert isinstance(self.kaffir.chat, objects.Chat)

    def test_subscribe(self):
        user = self.user
        assert user.subscribe().is_subscription == True
        user.unsubscribe()

    def test_unsubscribe(self):
        user = self.user
        user.subscribe()
        assert user.unsubscribe().is_subscription == False

    def test_block(self):
        assert self.user.block().is_blocked == True
        self.user.unblock()

    def test_redundant_block(self):
        assert self.user.block().block().is_blocked == True
        self.user.unblock()

    def test_unblock(self):
        self.user.block()
        assert self.user.unblock().is_blocked == False

    def test_redundant_unblock(self):
        self.user.block()
        assert self.user.unblock().unblock().is_blocked == False

    def test_block_installation(self):
        assert self.user.block("installation").is_blocked == True
        self.user.unblock()

    def test_redundant_block_installation(self):
        assert self.user.block("installation").block(
            "installation").is_blocked == True
        self.user.unblock()

    def test_block_invalid(self):
        with self.assertRaises(ValueError):
            self.user.block("foobar")

    def test_report_hate(self):
        assert isinstance(self.user.report("hate"), objects.User)

    def test_report_nude(self):
        assert isinstance(self.user.report("nude"), objects.User)

    def test_report_spam(self):
        assert isinstance(self.user.report("spam"), objects.User)

    def test_report_target(self):
        assert isinstance(self.user.report("target"), objects.User)

    def test_report_harm(self):
        assert isinstance(self.user.report("harm"), objects.User)

    def test_incorrect_report(self):
        with self.assertRaises(TypeError):
            self.user.report("foobar")

    def test_subscribe_to_updates(self):
        user = self.user
        assert user.subscribe_to_updates().is_updates_subscription == True
        user.unsubscribe_to_updates()

    def test_unsubscribe_to_updates(self):
        user = self.user
        user.subscribe_to_updates()
        assert user.unsubscribe_to_updates().is_updates_subscription == False

    def test_set_nick(self):
        new = f"foobar{random.randrange(100, 999)}"
        nick = self.client.user.nick
        assert self.client.user.set_nick(new).nick == new
        self.client.user.set_nick(nick)

    def test_set_nick_taken(self):
        with self.assertRaises(exceptions.Unavailable):
            self.client.user.set_nick("kaffir")

    def test_set_nick_empty(self):
        with self.assertRaises(exceptions.Unavailable):
            self.client.user.set_nick("")

    def test_set_nick_invalid(self):
        with self.assertRaises(exceptions.Unavailable):
            self.client.user.set_nick("f")

    def test_set_nick_bad_type(self):
        with self.assertRaises(exceptions.Unavailable):
            self.client.user.set_nick(random.randrange)

    def test_set_about(self):
        new = string.printable
        about = self.client.user.about
        assert self.client.user.set_about(new).about == new
        self.client.user.set_about(about)

    def test_set_private(self):
        assert self.client.user.set_private(True).is_private == True
        self.client.user.set_private(False)

    def test_is_private_setter(self):
        self.client.user.is_private = True
        assert self.client.user.is_private == True
        self.client.user.is_private = False

    def test_nick_setter(self):
        new = f"foobar{random.randrange(100, 999)}"
        nick = self.client.user.nick
        self.client.user.nick = new
        assert self.client.user.nick == new
        self.client.user.nick = nick

    def test_about_setter(self):
        new = string.printable
        about = self.client.user.about
        self.client.user.about = new
        assert self.client.user.about == new
        self.client.user.about = about

    def test_is_updates_subscription_setter(self):
        user = self.user
        user.is_updates_subscription = True
        assert user.is_updates_subscription == True
        user.is_updates_subscription = False

    def test_is_subscription_setter(self):
        user = self.user
        user.is_subscription = True
        assert user.is_subscription
        user.is_subscription = False
