import unittest
import random, threading, pathlib, os, shutil
from ifunny import objects
from ifunny.objects import _mixin as mixin


class ClientBaseTest(unittest.TestCase):
    def test_featured_paginated(self):
        limit = random.randrange(3, 10)
        client = mixin.ClientBase(paginated_size = limit)
        posts = client._featured_paginated()
        assert len(posts["items"]) == limit
        assert isinstance(posts["items"][0], objects.Post)
        assert isinstance(posts["paging"]["next"], str)

    def test_featured(self):
        post = next(mixin.ClientBase().featured)
        assert isinstance(post, objects.Post)
        assert post.is_featured

    # ifunny doesn't return all of the posts asked for in collective

    def test_collective_paginated(self):
        limit = random.randrange(30, 100)
        client = mixin.ClientBase(paginated_size = limit)
        posts = client._collective_paginated()
        assert isinstance(posts["items"][0], objects.Post)
        assert isinstance(posts["paging"]["next"], str)

    def test_collective(self):
        post = next(mixin.ClientBase().collective)
        assert isinstance(post, objects.Post)

    def test_digests_paginated(self):
        client = mixin.ClientBase()
        posts = client._digests_paginated()
        assert isinstance(posts["items"][0], objects.Digest)

    def test_digests(self):
        digest = next(mixin.ClientBase().digests)
        assert isinstance(digest, objects.Digest)

    def test_channels(self):
        channel = mixin.ClientBase().channels[0]
        assert isinstance(channel, objects.Channel)

    def test_trending_chats(self):
        chat = mixin.ClientBase().trending_chats[0]
        assert isinstance(chat, objects.Chat)

    def test_no_messenger_token(self):
        assert mixin.ClientBase().messenger_token is None

    def test_basic_token(self):
        client = mixin.ClientBase()
        client._config = {}
        assert len(client.basic_token) == 156

    def test_user_agent(self):
        assert isinstance(mixin.ClientBase()._user_agent, str)

    def test_headers(self):
        client = mixin.ClientBase()
        client._config = {}
        token = client.basic_token
        assert client.headers == {
            "Authorization": f"Basic {token}",
            "User-Agent": client._user_agent
        }

    def test_api(self):
        assert mixin.ClientBase().api == "https://api.ifunny.mobi/v4"

    def test_sendbird_api(self):
        assert mixin.ClientBase(
        ).sendbird_api == "https://api-us-1.sendbird.com/v3"

    def test_client_id(self):
        assert mixin.ClientBase()._ClientBase__client_id == "MsOIJ39Q28"

    def test_client_secret(self):
        assert mixin.ClientBase(
        )._ClientBase__client_secret == "PTDc3H8a)Vi=UYap"

    def test_config_lock(self):
        assert isinstance(mixin.ClientBase()._config_lock,
                          type(threading.Lock()))

    def test_sendbird_lock(self):
        assert isinstance(mixin.ClientBase()._sendbird_lock,
                          type(threading.Lock()))

    def test_home_path(self):
        assert mixin.ClientBase(
        )._home_path == f"{pathlib.Path.home()}/.ifunnypy"

    def test_cache_path_create(self):
        assert mixin.ClientBase(
        )._cache_path == f"{mixin.ClientBase()._home_path}/config.json"

    def test_home_path_create(self):
        shutil.rmtree(mixin.ClientBase()._home_path, ignore_errors = True)
        assert os.path.isdir(mixin.ClientBase()._home_path)

    def test_home_path_exists(self):
        shutil.rmtree(mixin.ClientBase()._home_path, ignore_errors = True)
        assert os.path.isfile(mixin.ClientBase()._cache_path)

    def test_unread_features(self):
        assert mixin.ClientBase().unread_featured >= 0

    def test_mark_features_read(self):
        client = mixin.ClientBase()
        client.mark_features_read()
        assert client.unread_featured == 0

    def test_unread_collective(self):
        assert mixin.ClientBase().unread_collective > 0

    # search methods may misbehave, ifunny is on some sort of lockdown

    def _test_search_users_paginated(self):
        # ifunny seems to have disabled searching
        client = mixin.ClientBase()
        posts = client._search_users_paginated("removeddit")
        assert isinstance(posts["items"][0], objects.User)
        assert posts["items"][0].nick == "removeddit"

    def _test_search_users(self):
        # ifunny seems to have disabled searching
        search = mixin.ClientBase().search_users("removeddit")
        result = next(search)
        assert isinstance(result, objects.User)
        assert result.nick == "removeddit"

    def test_search_tags_paginated(self):
        client = mixin.ClientBase()
        posts = client._search_tags_paginated("meme")
        assert isinstance(posts["items"][0], objects.Post)

    def test_search_tags(self):
        search = mixin.ClientBase().search_tags("meme")
        assert isinstance(next(search), objects.Post)

    def test_search_chats_paginated(self):
        client = mixin.ClientBase()
        posts = client._search_chats_paginated("meme")
        assert isinstance(posts["items"][0], objects.Chat)

    def test_search_chats(self):
        search = mixin.ClientBase().search_chats("meme")
        assert isinstance(next(search), objects.Chat)


if __name__ == '__main__':
    unittest.main()
