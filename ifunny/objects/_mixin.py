import json, requests, threading, os, time

from random import random
from hashlib import sha1
from base64 import b64encode
from pathlib import Path

from ifunny import objects
from ifunny.util import methods, exceptions


class ClientBase:
    """
    iFunny Client base class.
    Also used standalone for some read-only actions that do not warrant a Client that may log in

    :param paginated_size: default number of elemets to request for each paginated data call
    :captcha_api_key: 2captcha api key to use for attempts at creating accounts

    :type paginated_size: int
    :type captcha_api_key: str
    """
    api = "https://api.ifunny.mobi/v4"
    sendbird_api = "https://api-us-1.sendbird.com/v3"
    captcha_api = "https://2captcha.com"
    _user_agent = "iFunny/5.42(1117792) Android/5.0.2 (samsung; SCH-R530U; samsung)"
    __client_id = "MsOIJ39Q28"
    __client_secret = "PTDc3H8a)Vi=UYap"
    __google_code = "6LflIwgTAAAAAElWMFEVgr9zs2UpH0eiFsVN_KfF"

    def __init__(self, paginated_size = 25, captcha_api_key = None):
        # locks
        self._sendbird_lock = threading.Lock()
        self._config_lock = threading.Lock()

        # api info
        self.captcha_api_key = captcha_api_key
        self.authenticated = False
        self._new_basic = False

        # cache file
        self._home_path = f"{Path.home()}/.ifunnypy"
        self._cache_path = f"{self._home_path}/config.json"

        # attached objects
        self.paginated_size = paginated_size

        if not os.path.isdir(self._home_path):
            os.mkdir(self._home_path)

        try:
            with open(self._cache_path) as stream:
                self._config = json.load(stream)

        except (FileNotFoundError):
            self._config = {}
            self._update_config()

    # private methods

    def _update_config(self):
        """
        Update the config file with the internal config dict in a thread safe way
        """
        self._config_lock.acquire()

        with open(self._cache_path, "w") as stream:
            json.dump(self._config, stream)

        self._config_lock.release()

    def _solve_captcha(self, url, timeout = 64):
        params = {
            "key": self.captcha_api_key,
            "googlekey": self.__google_code,
            "pageurl": url,
            "method": "userrecaptcha"
        }

        data = {"key": self.captcha_api_key, "json": 1}

        id = requests.post(f"{self.captcha_api}/in.php",
                           data = data,
                           params = params).json()["request"]

        params = {
            "action": "get",
            "id": id,
            "json": 1,
            "key": self.captcha_api_key
        }

        while timeout:
            timeout -= 2
            result = requests.get(f"{self.captcha_api}/res.php",
                                  params = params).json()["request"]

            if result != "CAPCHA_NOT_READY":
                return result

            time.sleep(2)

        raise Exception("took too long solving")

    @property
    def new_basic_token(self):
        """
        Generate a new basic token, even if one is stored

        :returns: Basic oauth2 token
        :rtype: string
        """
        self._new_basic = True
        return self.basic_token

    @property
    def basic_token(self):
        """
        Generate or load from config a Basic auth token.

        :returns: Basic oauth2 token
        :rtype: str
        """
        if self._config.get("login_token") and not self._new_basic:
            return self._config["login_token"]

        hex_string = os.urandom(32).hex().upper()
        hex_id = f"{hex_string}_{self.__client_id}"
        hash_decoded = f"{hex_string}:{self.__client_id}:{self.__client_secret}"
        hash_encoded = sha1(hash_decoded.encode('utf-8')).hexdigest()
        self._config["login_token"] = b64encode(
            bytes(f"{hex_id}:{hash_encoded}", 'utf-8')).decode()

        self._update_config()

        return self._config["login_token"]

    @property
    def headers(self):
        """
        Generate headers for iFunny requests dependant on authentication

        :returns: request-ready headers
        :rtype: dict
        """
        return {
            "Authorization": f"Basic {self.basic_token}",
            "User-Agent": self._user_agent
        }

    def _notifications_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/news/my",
                                      "news",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            objects.Notification(item, client = self) for item in data["items"]
        ]

        return methods.paginated_format(data,
                                        items)  # test with another account

    def _chats_paginated(self,
                         limit = 100,
                         next = None,
                         prev = None,
                         show_empty = True,
                         show_read_recipt = True,
                         show_member = True,
                         public_mode = "all",
                         super_mode = "all",
                         distinct_mode = "all",
                         member_state_filter = "all",
                         order = "latest_last_message"):
        limit = limit if limit else self.paginated_size

        params = {
            "limit": limit,
            "token": next,
            "show_empty": show_empty,
            "show_read_recipt": show_read_recipt,
            "show_member": show_member,
            "public_mode": public_mode,
            "super_mode": super_mode,
            "distinct_mode": distinct_mode,
            "member_state_filter": member_state_filter,
            "order": order
        }

        url = f"{self.sendbird_api}/users/{self.id}/my_group_channels"

        response = requests.get(url,
                                params = params,
                                headers = self.sendbird_headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        response = response.json()

        paging = {"next": response["next"]}

        return {
            "paging":
            paging,
            "items": [
                objects.Chat(data["channel_url"], self, data = data)
                for data in response["channels"]
            ]
        }  # test chat

    def _reads_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/feeds/reads",
                                      "content",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            objects.Post(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _collective_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/feeds/collective",
                                      "content",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next,
                                      post = True)

        items = [
            objects.Post(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _featured_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/feeds/featured",
                                      "content",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            objects.Post(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _digests_paginated(self, limit = None, next = None, prev = None):
        data = methods.paginated_data(f"{self.api}/digest_groups",
                                      None,
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next,
                                      ex_params = {"contents": 0})

        nested = [item["items"] for item in data["items"]]
        data["items"] = [item for sublist in nested for item in sublist]

        items = [
            objects.Digest(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _search_tags_paginated(self,
                               query,
                               limit = 30,
                               next = None,
                               prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/search/content",
                                      "content",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next,
                                      ex_params = {"tag": query})

        items = [
            objects.Post(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _search_users_paginated(self,
                                query,
                                limit = 50,
                                next = None,
                                prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/search/users",
                                      "users",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next,
                                      ex_params = {"q": query})

        items = [
            objects.User(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _search_chats_paginated(self,
                                query,
                                limit = 20,
                                next = None,
                                prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/search/chats/channels",
                                      "channels",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next,
                                      ex_params = {"q": query})

        items = [
            objects.Chat(item["channel_url"], self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def search_users(self, query):
        """
        Search for users

        :param query: query to search

        :type query: str

        :returns: generator iterating search results
        :rtype: generator<User>
        """
        return methods.paginated_generator(self._search_users_paginated, query)

    def search_tags(self, query):
        """
        Search for tags

        :param query: query to search

        :type query: str

        :returns: generator iterating search results
        :rtype: generator<Post>
        """
        return methods.paginated_generator(self._search_tags_paginated, query)

    def search_chats(self, query):
        """
        Search for chats

        :param query: query to search

        :type query: str

        :returns: generator iterating search results
        :rtype: generator<Chat>
        """
        return methods.paginated_generator(self._search_chats_paginated, query)

    def mark_features_read(self):
        """
        Mark featured feed as read (or viewed).
        """
        response = requests.put(f"{self.api}/reads/all",
                                headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

    def email_is_available(self, email):
        """
        Check email availability
        :param email: email in question

        :type email: str

        :returns: is this email available?
        :rtype: bool
        """
        params = {"email": email}

        response = requests.get(f"{self.api}/users/emails_available",
                                headers = self.headers,
                                params = params)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return response.json()["data"]["available"]

    def nick_is_available(self, nick):
        """
        Check nick availability
        :param nick: nick in question

        :type nick: str

        :returns: is this nick available?
        :rtype: bool
        """
        params = {"nick": nick}

        response = requests.get(f"{self.api}/users/nicks_available",
                                headers = self.headers,
                                params = params)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return response.json()["data"]["available"]

    @property
    def notifications(self):
        """
        generator for a client's notifications.
        Each iteration will return the next notification, in decending order of date recieved

        :returns: generator iterating through notifications
        :rtype: generator<Notification>
        """
        return methods.paginated_generator(
            self._notifications_paginated)  # test with another account

    @property
    def reads(self):
        """
        generator for a client's reads.
        Each iteration will return the next viewed post, in decending order of date accessed

        :returns: generator iterating through read posts
        :rtype: generator<Post>
        """
        return methods.paginated_generator(
            self._reads_paginated)  # test with another account

    @property
    def viewed(self):
        """
        Alias to Client.reads because ifunny's in-api name is dumb.
        You don't read a picture or video
        """
        return self.reads  # test with another account

    @property
    def collective(self):
        """
        generator for the collective feed.
        Each iteration will return the next collective post, in decending order of date posted

        :returns: generator iterating the collective feed
        :rtype: generator<Post>
        """
        return methods.paginated_generator(self._collective_paginated)

    @property
    def featured(self):
        """
        generator for the featured feed.
        Each iteration will return the next featured post, in decending order of date posted

        :returns: generator iterating the featured feed
        :rtype: generator<Post>
        """
        return methods.paginated_generator(self._featured_paginated)

    @property
    def digests(self):
        """
        :returns: digests available to the client from explore
        :rtype: generator<Digest>
        """
        return methods.paginated_generator(self._digests_paginated)

    @property
    def channels(self):
        """
        :returns: a list of channels featured in explore
        :rtype: list<Channel>
        """
        response = requests.get(f"{self.api}/channels", headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return [
            objects.Channel(data["id"], client = self, data = data)
            for data in response.json()["data"]["channels"]["items"]
            if data["id"] != "latest_digest"
        ]  # TODO: why is this not returning a generator? woner what my logic was

    @property
    def trending_chats(self):
        """
        :returns: a list of trending chats featured in explore
        :rtype: list<Chat>
        """
        response = requests.get(f"{self.api}/chats/channels/trending",
                                headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return [
            objects.Chat(data["channel_url"], self, data = data)
            for data in response.json()["data"]["channels"]
        ]

    @property
    def messenger_token(self):
        return None

    @property
    def counters(self):
        """
        :returns: ifunny unread counters
        :rtype: dict
        """
        response = requests.get(f"{self.api}/counters", headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return response.json().get("data")

    @property
    def unread_featured(self):
        """
        :returns: unread featured posts
        :rtype: int
        """
        return self.counters.get("featured", 0)

    @property
    def unread_collective(self):
        """
        :returns: unread collective posts
        :rtype: int
        """
        return self.counters.get("collective", 0)

    @property
    def unread_subscriptions(self):
        """
        :returns: unread subscriptions posts
        :rtype: int
        """
        return self.counters.get("subscriptions", 0)

    @property
    def unread_news(self):
        """
        :returns: unread news posts
        :rtype: int
        """
        return self.counters.get("news", 0)


class ObjectMixin:
    """
    Mixin class for iFunny objects.
    Used to implement common methods

    :param id: id of the object
    :param client: Client that the object belongs to
    :param data: A data payload for the object to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    api = "https://api.ifunny.mobi/v4"

    def __init__(self,
                 id,
                 client = ClientBase(),
                 data = None,
                 paginated_size = 30):
        self.client = client
        self.id = id

        self._object_data_payload = data
        self._update = data is None

        self._url = None

        self.paginated_size = paginated_size

        self.__home_path = f"{Path.home()}/.ifunnypy"
        self.__cache_path = f"{self.__home_path}/config.json"

    def _get_prop(self, key, default = None):
        if not self._object_data.get(key, None):
            self._update = True

        return self._object_data.get(key, default)

    def __eq__(self, other):
        return self.id == other

    @property
    def _object_data(self):
        if self._update or self._object_data_payload is None:
            self._update = False
            response = requests.get(self._url, headers = self.headers)

            try:
                self._object_data_payload = response.json()["data"]
            except KeyError:
                raise exceptions.BadAPIResponse(
                    f"{response.url}, {response.text}")

        return self._object_data_payload

    @property
    def fresh(self):
        """
        :returns: self after setting the update flag
        :rtype: Subclass of ObjectMixin
        """
        self._update = True
        return self

    @property
    def is_deleted(self):
        """
        :returns: is this object deleted?
        :rtype: bool
        """
        return self._get_prop("is_deleted", default = False)

    @property
    def headers(self):
        return self.client.headers


class CommentMixin(ObjectMixin):
    """
    Mixin class for iFunny comments objects.
    Used to implement common methods, subclass to ObjectMixin

    :param id: id of the object
    :param client: Client that the object belongs to
    :param data: A data payload for the object to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead
    :param post: post that the comment belongs to, if no  data payload supplied
    :param root: if comment is a reply, the root comment

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    :type post: str or Post
    :type root: str
    """
    def __init__(self,
                 id,
                 client = ClientBase(),
                 data = None,
                 paginated_size = 30,
                 post = None,
                 root = None):
        super().__init__(id,
                         client = client,
                         data = data,
                         paginated_size = paginated_size)
        self._post = post
        self._root = root

    @property
    def _object_data(self):
        if self._update or self._object_data_payload is None:
            self._update = False
            response = requests.get(self._url, headers = self.headers)

            try:
                self._object_data_payload = response.json()["data"]["comment"]
            except KeyError:
                raise exceptions.BadAPIResponse(
                    f"{response.url}, {response.text}")

        return self._object_data_payload


class SendbirdMixin(ObjectMixin):
    """
    Mixin class for sendbird objects.
    Used to implement common methods, subclass to ObjectMixin

    :param id: id of the object
    :param client: Client that the object belongs to
    :param data: A data payload for the object to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self,
                 id,
                 client = ClientBase(),
                 data = None,
                 paginated_size = 30):
        super().__init__(id,
                         client = client,
                         data = data,
                         paginated_size = paginated_size)

    @property
    def _object_data(self):
        if self._update or self._object_data_payload is None:
            if not self.client.messenger_token:
                raise exceptions.ChatNotActive(
                    "Chat must have been activated to get sendbird api token")

            self._update = False
            response = requests.get(self._url,
                                    headers = self.client.sendbird_headers)

            if response.status_code == 403:
                self._object_data_payload = {}
                return self._object_data_payload

            try:
                self._object_data_payload = response.json()
            except KeyError:
                raise exceptions.BadAPIResponse(
                    f"{response.url}, {response.text}")

        return self._object_data_payload
