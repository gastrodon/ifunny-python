import json, os, threading, time
import requests

from random import random
from hashlib import sha1
from base64 import b64encode
from importlib import import_module
from pathlib import Path

from ifunny.client._handler import Handler, Event
from ifunny.client._sendbird import Socket
from ifunny.ext.commands import Command, Defaults
from ifunny.objects import User, Post, Comment, Notification, Channel, Digest, Chat
from ifunny.util.methods import paginated_format, paginated_data, paginated_generator
from ifunny.util.exceptions import ChatAlreadyActive, BadAPIResponse, ChatNotActive

class Client:
    """
    iFunny client used to do most things.

    :param trace: enable websocket_client trace? (debug)
    :param threaded: False to have all socket callbacks run in the same thread for debugging
    :param prefix: Static string or callable prefix for chat commands
    :param paginated_size: Number of items to request in paginated methods

    :type trace: bool
    :type threaded: bool
    :type prefix: str or callable
    :type paginated_size: int
    """
    api = "https://api.ifunny.mobi/v4"
    sendbird_api = "https://api-us-1.sendbird.com/v3"
    __client_id = "MsOIJ39Q28"
    __client_secret = "PTDc3H8a)Vi=UYap"
    __user_agent = "iFunny/5.38.1(1117733) Android/9 (OnePlus; ONEPLUS A6013; OnePlus)"

    commands = {
        "help" : Defaults.help
    }

    def __init__(self, trace = False, threaded = True, prefix = {""}, paginated_size = 25):
        # command
        self.__prefix = None
        self.prefix = prefix

        # locks
        self.__sendbird_lock = threading.Lock()
        self.__config_lock = threading.Lock()

        # api info
        self.authenticated = False
        self.__token = None
        self.__id = None

        # sendbird api info
        self.sendbird_session_key = None
        self.__messenger_token = None
        self.__sendbird_req_id = int(time.time() * 1000 + random() * 1000000)

        # attatched objects
        self.paginated_size = paginated_size

        self.handler = Handler(self)

        self.socket = Socket(self, trace, threaded)

        # own profile data
        self.__user = None
        self._account_data_payload = None
        self._update = False

        # cache file
        self.__home_path = f"{Path.home()}/.ifunnypy"
        self.__cache_path = f"{self.__home_path}/config.json"

        if not os.path.isdir(self.__home_path):
            os.mkdir(self.__home_path)

        try:
            with open(self.__cache_path) as stream:
                self.__config = json.load(stream)

        except (FileNotFoundError):
            self.__config = {}
            self.__update_config()

    def __repr__(self):
        return self.user.nick

    # private methods

    def __update_config(self):
        """
        Update the config file with the internal config dict in a thread safe way
        """
        self.__config_lock.acquire()

        with open(self.__cache_path, "w") as stream:
            json.dump(self.__config, stream)

        self.__config_lock.release()

    def _get_prop(self, key, force = False):
        if not self.__account_data.get(key, None) or force:
            self._update = True

        return self.__account_data.get(key, None)

    def _notifications_paginated(self, limit = 400, prev = None, next = None):
        limit = min(limit, self.paginated_size)
        data = paginated_data(
            f"{self.api}/news/my", "news", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Notification(item, self) for item in data["items"]]

        return paginated_format(data, items)

    def _chats_paginated(self, limit = 100, next = None, prev = None, show_empty = True, show_read_recipt = True, show_member = True, public_mode = "all", super_mode = "all", distinct_mode = "all", member_state_filter = "all", order = "latest_last_message"):
        limit = min(limit, 100)

        params = {
            "limit":                limit,
            "token":                next,
            "show_empty":           show_empty,
            "show_read_recipt":     show_read_recipt,
            "show_member":          show_member,
            "public_mode":          public_mode,
            "super_mode":           super_mode,
            "distinct_mode":        distinct_mode,
            "member_state_filter":  member_state_filter,
            "order":                order
        }

        url = f"{self.sendbird_api}/users/{self.id}/my_group_channels"

        response = requests.get(url, params = params, headers = self.sendbird_headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        response = response.json()

        paging = {
            "next": response["next"]
        }

        return {
            "paging":   paging,
            "items": [Chat(data["channel_url"], self, data = data) for data in response["channels"]]
        }

    def _reads_paginaged(self, limit = 30, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/feeds/reads", "content", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _collective_paginated(self, limit = 375, next = None, prev = None):
        limit = min(limit, self.paginated_size)
        data = paginated_data(
            f"{self.api}/feeds/collective", "content", self.headers,
            limit = limit, prev = prev, next = next, post = True
        )

        items = [Post(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _featured_paginated(self, limit = 30, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/feeds/featured", "content", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _home_paginated(self, limit = 100, next = None, prev = None):
        limit = min(limit, self.paginated_size)
        data = paginated_data(
            f"{self.api}/timelines/home", "content", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _digests_paginated(self, limit = 5, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/digest_groups", None, self.headers,
            limit = limit, prev = prev, next = next, ex_params = {"contents": 0}
        )

        items = [Digest(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _search_tags_paginated(self, query, limit = 30, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/search/content", "content", self.headers,
            limit = limit, prev = prev, next = next, ex_params = {"tag": query}
        )

        items = [Post(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _search_users_paginated(self, query, limit = 50, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/search/users", "users", self.headers,
            limit = limit, prev = prev, next = next, ex_params = {"q": query}
        )

        items = [User(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _search_chats_paginated(self, query, limit = 20, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/search/chats/channels", "channels", self.headers,
            limit = limit, prev = prev, next = next, ex_params = {"q": query}
        )

        items = [Chat(item["channel_url"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _smiles_paginated(self, limit = 30, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/users/my/content_smiles", "content", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _comments_paginated(self, limit = 30, next = None, prev = None):
        limit = self.paginated_size
        data = paginated_data(
            f"{self.api}/users/my/content_smiles", "content", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self, data = item, post = data["cid"], root = data.get("root_comm_id")) for item in data["items"]]

        return paginated_format(data, items)

    # private properties

    @property
    def __login_token(self):
        """
        Generate or load from config a Basic auth token

        returns
            string
        """
        if self.__config.get("login_token"):
            return self.__config["login_token"]

        hex_string = os.urandom(36).hex().upper()
        hex_id = f"{hex_string}_{self.__client_id}"
        hash_decoded = f"{hex_string}:{self.__client_id}:{self.__client_secret}"
        hash_encoded = sha1(hash_decoded.encode('utf-8')).hexdigest()
        self.__config["login_token"] = b64encode(bytes(f"{hex_id}:{hash_encoded}", 'utf-8')).decode()

        self.__update_config()

        return self.__config["login_token"]

    @property
    def __account_data(self):
        """
        Get existing or request new account data

        returns
            dict
        """
        if self._update or self._account_data_payload is None:
            self._update = False
            self._account_data_payload = requests.get(f"{self.api}/account", headers = self.headers).json()["data"] if self.authenticated else {}

        return self._account_data_payload

    # public methods

    def login(self, email, password, force = False):
        """
        Authenticate with iFunny to get an API token.
        Will try to load saved account tokens (saved as plaintext json, indexed by `email_token`) if `force` is False

        :param email: Email associated with the account
        :param password: Password associated with the account
        :param force: Ignore saved Bearer tokens?

        :type email: str
        :type password: str
        :type force: bool
        """

        if self.authenticated:
            raise AlreadyAuthenticated(f"This client instance already authenticated as {self.nick}")

        if not force and self.__config.get(f"{email}_token"):
            self.__token = self.__config[f"{email}_token"]
            response = requests.get(f"{self.api}/account", headers = self.headers)

            if response.status_code == 200:
                self.authenticated = True
                return self

        headers = {
            "Authorization": f"Basic {self.__login_token}"
        }

        data = {
            "grant_type": "password",
            "username": email,
            "password": password
        }

        response = requests.post(f"{self.api}/oauth2/token", headers = headers, data = data)

        if response.status_code == 403:
            time.sleep(10)
            response = requests.post(f"{self.api}/oauth2/token", headers = headers, data = data)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        self.__token = response.json()["access_token"]
        self.authenticated = True
        self.__config[f"{email}_token"] = self.__token

        self.__update_config()
        return self

    def post_image_url(self, image_url, **kwargs):
        """
        Post an image from a url to iFunny

        :param image_url: location image to post
        :param tags: list of searchable tags
        :param visibility: Visibility of the post on iFunny. Can be one of (``public``, ``subscribers``)
        :param wait: wait for the post to be successfuly published?
        :param timeout: time to wait for a successful post
        :param schedule: timestamp to schedule the post for, or None for immediate

        :type image_data: bytes
        :type tags: list<str>
        :type visibility: str
        :type wait: bool
        :type timeout: int
        :type schedule: int, or None

        :returns: Post if wait flag set (when posted)
        :rtype: Post, or None
        """
        image_data = requests.get(image_url).content

        return self.post_image(image_data, **kwargs)

    def post_image(self, image_data, tags = [], visibility = "public", wait = False, timeout = 15, schedule = None):
        """
        Post an image to iFunny

        :param image_data: Binary image to post
        :param tags: List of searchable tags
        :param visibility: Visibility of the post on iFunny. Can be one of (``public``, ``subscribers``)
        :param wait: wait for the post to be successfuly published?
        :param timeout: time to wait for a successful post
        :param schedule: timestamp to schedule the post for, or None for immediate

        :type image_data: bytes
        :type tags: list<str>
        :type visibility: str
        :type wait: bool
        :type timeout: int
        :type schedule: int, or None

        :returns: Post if wait flag set (when posted)
        :rtype: Post, or None
        """
        if visibility not in {"public", "subscribers"}:
            raise ValueError(f"visibility cannot be {visibility}")

        data = {
            "type": "pic",
            "tags": json.dumps(tags),
            "visibility": visibility
        }

        if schedule:
            data["publish_at"] = int(schedule)

        files = {
            "image": image_data
        }

        response = requests.post(f"{self.api}/content", headers = self.headers, data = data, files = files)
        id = response.json()["data"]["id"]
        posted = None

        if not wait:
            return

        while timeout * 2:
            response = requests.get(f"{self.api}/tasks/{id}", headers = self.headers).json()["data"]

            if response.get("result"):
                return Post(response["result"]["cid"], self)

            time.sleep(.5)
            timeout -= 1

    def resolve_command(self, message):
        """
        Find and call a command called from a message

        :param message: Message object recieved from the sendbird socket

        :type message: Message
        """
        parsed = message.content.split(" ")
        first, args = parsed[0], parsed[1:]

        for prefix in self.prefix:
            if first.startswith(prefix):
                return self.commands.get(first[len(prefix):], Defaults.default)(message, args)

    def mark_features_read(self):
        """
        Mark all features as read (or viewed).
        """
        response = requests.put(f"{self.api}/reads/all")

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

    def search_users(self, query):
        """
        Search for users

        :param query: query to search

        :type query: str

        :returns: generator iterating search results
        :rtype: generator<User>
        """
        return paginated_generator(self._search_users_paginated, query)

    def search_tags(self, query):
        """
        Search for tags

        :param query: query to search

        :type query: str

        :returns: generator iterating search results
        :rtype: generator<Post>
        """
        return paginated_generator(self._search_tags_paginated, query)

    def search_chats(self, query):
        """
        Search for chats

        :param query: query to search

        :type query: str

        :returns: generator iterating search results
        :rtype: generator<Chat>
        """
        return paginated_generator(self._search_chats_paginated, query)

    def suggested_tags(self, query):
        """
        Tags suggested by ifunny for a query

        :param query: query for suggested tags

        :type query: str

        :returns: list of suggested tags and the number of memes with it
        :rty: list<tuple<str, int>>
        """
        params = {
            "q"     : str(query)
        }

        response = requests.get(f"{self.api}/tags/suggested", params = params, headers = self.headers)

        return [(item["tag"], item["uses"]) for item in response.json()["data"]["tags"]["items"]]

    # sendbird methods

    def start_chat(self):
        """
        Start the chat websocket connection.

        :returns: this client's socket object
        :rtype: Socket

        :raises: Exception stating that the socket is already alive
        """
        if self.socket.active:
            raise ChatAlreadyActive("Already started")

        if not self.messenger_token:
            self.messenger_token = self.__account_data["messenger_token"]

        return self.socket.start()

    def stop_chat(self):
        """
        Stop the chat websocket connection.

        :returns: this client's socket object
        :rtype: Socket
        """
        return self.socket.stop()

    def sendbird_upload(self, chat, file_data):
        """
        Upload an image to sendbird for a specific chat

        :param chat: chat to upload the file for
        :param file_data: binary file to upload

        :type chat: ifunny.objects.Chat
        :type file_data: bytes

        :returns: url to the uploaded content
        :rtype: str
        """
        files = {
            "file": file_data
        }

        data = {
            "thumbnail1"    : "780, 780",
            "thumbnail2"    : "320,320",
            "channel_url"   : chat.channel_url
        }

        response = requests.post(f"{self.sendbird_api}/storage/file", headers = self.sendbird_headers, files = files, data = data)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return response.json()["url"]

    # public decorators

    def command(self, name = None):
        """
        Decorator to add a command, callable in chat with the format ``{prefix}{command}``
        Commands must take two arguments, which are set as the Message and list<str> of space-separated words in the message (excluding the command) respectively::

            import ifunny
            robot = ifunny.Client()

            @robot.command()
            def some_command(ctx, args):
                # do something
                pass

        :param name: Name of the command callable from chat. If None, the name of the function will be used instead.

        :type name: str
        """
        def _inner(method):
            _name = name if name else method.__name__
            self.commands[_name] = Command(method, _name)

        return _inner

    def event(self, name = None):
        """
        Decorator to add an event, which is called when different things happen by the clients socket.
        Events must take one argument, which is a dict with the websocket data::

            import ifunny
            robot = ifunny.Client()

            @robot.event(name = "on_connect")
            def event_when_connected_to_chat(data):
                print(f"{robot} is chatting")

        :param name: Name of the event. If None, the name of the function will be used instead. See the Sendbird section of the docs for valid events.

        :type name: str
        """
        def _inner(method):
            _name = name if name else method.__name__
            self.handler.events[_name] = Event(method, _name)

        return _inner

    # public properties

    @property
    def sendbird_headers(self):
        """
        Generate headers for a sendbird api call.
        If a sendbird_session_key exists, it's added

        :returns: sendbird-ready headers
        :rtype: dict
        """
        _headers = {
            "User-Agent": "jand/3.096"
        }

        if self.sendbird_session_key:
            _headers["Session-Key"] = self.sendbird_session_key

        return _headers

    @property
    def headers(self):
        """
        Generate headers for iFunny requests dependant on authentication

        :returns: request-ready headers
        :rtype: dict
        """
        _headers = {
            "User-Agent"    : self.__user_agent,
        }

        _headers["Authorization"] = f"Bearer {self.__token}" if self.__token else f"Basic {self.__login_token}"

        return _headers

    @property
    def prefix(self):
        """
        Get a set of prefixes that this bot can use.
        Each one is evaluated when handling a potential command

        :returns: prefixes that can be used to resolve commands
        :rtype: set
        """
        _pref = self.__prefix

        if callable(_pref):
            _pref = self.__prefix()

        if isinstance(_pref, (set, tuple, list, str)):
            return set(self.__prefix)

        raise TypeError(f"prefix must be str, iterable, or callable resulting in either. Not {type(_pref)}")

    @prefix.setter
    def prefix(self, value):
        """
        Set a set of prefixes that this bot can use.
        Each one is evaluated when handling a potential command

        :returns: prefixes that can be used to resolve commands
        :rtype: set
        """
        _pref = value

        if callable(value):
            _pref = value()

        if isinstance(_pref, (set, tuple, list, str)):
            self.__prefix = value
            return set(_pref)

        raise TypeError(f"prefix must be str, iterable, or callable resulting in either. Not {type(_pref)}")

    @property
    def messenger_token(self):
        """
        Get the messenger_token used for sendbird api calls
        If a value is not stored in self.__messenger_token, one will be fetched from the client account data and stored

        :returns: messenger_token
        :rtype: str
        """
        if not self.__messenger_token:
            self.__messenger_token = self.__account_data["messenger_token"]

        return self.__messenger_token

    @property
    def unread_notifications(self):
        """
        Get all unread notifications (notifications that have not been recieved from a GET) and return them in a list

        :returns: unread notifications
        :rtype: list<Notification>
        """
        unread = []
        generator = self.notifications

        for _ in range(self.unread_notifications_count):
            unread.append(next(generator))

        return unread

    @property
    def next_req_id(self):
        """
        Generate a new (sequential) sendbird websocket req_id in a thread safe way

        :returns: req_id
        :rtype: str
        """
        self.__sendbird_lock.acquire()
        self.__sendbird_req_id += 1
        self.__sendbird_lock.release()
        return self.__sendbird_req_id

    @property
    def user(self):
        """
        :returns: this client's user object
        :rtype: User
        """
        if not self.__user :
            self.__user = User(self.id, self, paginated_size = self.paginated_size)

        return self.__user

    @property
    def unread_notifications_count(self):
        """
        :returns: number of unread notifications
        :rtype: int
        """
        return requests.get(f"{self.api}/counters", headers = self.headers).json()["data"]["news"]

    @property
    def nick(self):
        """
        :returns: this client's username (``nick`` name)
        :rtype: str
        """
        return self._get_prop("nick")

    @property
    def email(self):
        """
        :returns: this client's associated email
        :rtype: str
        """
        return self._get_prop("email")

    @property
    def id(self):
        """
        :returns: this client's unique id
        :rtype: str
        """
        if not self.__id:
            self.__id = self._get_prop("id")

        return self.__id

    @property
    def fresh(self):
        """
        Sets the update flag for this client, and returns it. Useful for when new information is pertanent

        :returns: self
        :rtype: Client
        """
        self._update = True
        return self

    @property
    def trending_chats(self):
        """
        :returns: a list of trending chats featured in explore
        :rtype: list<Chat>
        """
        response = requests.get(f"{self.api}/chats/channels/trending", headers = self.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return [Chat(data["channel_url"], self, data = data) for data in response.json()["data"]["channels"]]

    @property
    def channels(self):
        """
        :returns: a list of channels featured in explore
        :rtype: list<Channel>
        """
        response = requests.get(f"{self.api}/channels", headers = self.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return [Channel(data["id"], self, data = data) for data in response.json()["data"]["channels"]["items"]]

    # public generators

    @property
    def notifications(self):
        """
        generator for a client's notifications.
        Each iteration will return the next notification, in decending order of date recieved

        :returns: generator iterating through notifications
        :rtype: generator<Notification>
        """
        return paginated_generator(self._notifications_paginated)

    @property
    def reads(self):
        """
        generator for a client's reads.
        Each iteration will return the next viewed post, in decending order of date accessed

        :returns: generator iterating through read posts
        :rtype: generator<Post>
        """
        return paginated_generator(self._reads_paginaged)

    @property
    def viewed(self):
        """
        Alias to Client.reads because ifunny's in-api name is dumb.
        You don't read a picture or video
        """
        return self.reads

    @property
    def home(self):
        """
        generator for a client's subscriptions feed (home feed).
        Each iteration will return the next home post, in decending order of date posted

        :returns: generator iterating the home feed
        :rtype: generator<Post>
        """
        return paginated_generator(self._home_paginated)

    @property
    def collective(self):
        """
        generator for the collective feed.
        Each iteration will return the next collective post, in decending order of date posted

        :returns: generator iterating the collective feed
        :rtype: generator<Post>
        """
        return paginated_generator(self._collective_paginated)

    @property
    def featured(self):
        """
        generator for the featured feed.
        Each iteration will return the next featured post, in decending order of date posted

        :returns: generator iterating the featured feed
        :rtype: generator<Post>
        """
        return paginated_generator(self._featured_paginated)

    @property
    def chats(self):
        """
        generator for a Client's chats.
        Each iteration will return the next chat, in order of last message

        :returns: generator iterating through chats
        :rtype: generator<Chat>
        """
        if not self.sendbird_session_key:
            raise ChatNotActive("Chat must be started at least once to get a session key")

        return paginated_generator(self._chats_paginated)

    @property
    def digests(self):
        """
        :returns: digests available to the client from explore
        :rtype: generator<Digest>
        """
        return paginated_generator(self._digests_paginated)

    @property
    def smiles(self):
        """
        :returns: generator iterating posts that this client has smiled
        :rtype: generator<Post>
        """
        return paginated_generator(self._smiles_paginated)

    @property
    def comments(self):
        """
        :returns: generator iterating comments that this client has left
        :rtype: generator<Comment>
        """
        return paginated_generator(self._comments_paginated)

    @property
    def timeline(self):
        """
        Alias for ``self.user.timeline``
        """
        return self.user.timeline
