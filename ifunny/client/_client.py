import json, time
import requests

from random import random
from hashlib import sha1
from base64 import b64encode
from pathlib import Path

from ifunny import objects
from ifunny.util import methods, exceptions
from ifunny.ext import commands
from ifunny.client import _handler as handler
from ifunny.client import _sendbird as sendbird


class Client(objects._mixin.ClientBase):
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
    commands = {"help": commands.Defaults.help}

    def __init__(self,
                 trace = False,
                 threaded = True,
                 prefix = {""},
                 paginated_size = 25,
                 captcha_api_key = None):
        super().__init__(paginated_size = paginated_size,
                         captcha_api_key = captcha_api_key)
        # command
        self.__prefix = None
        self.prefix = prefix

        # api info
        self.__token = None
        self.__id = None

        # sendbird api info
        self.__messenger_token = None
        self.__sendbird_req_id = int(time.time() * 1000 + random() * 1000000)

        # attatched objects

        self.handler = handler.Handler(self)

        self.socket = sendbird.Socket(self, trace, threaded)

        # own profile data
        self.__user = None
        self._object_data_payload = None
        self._update = False

    def __repr__(self):
        return self.user.nick

    # private methods

    def _achievements_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self.api}/users/my/achievements",
                                      None,
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            objects.Achievement(item["id"], client = self, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _home_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/timelines/home",
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

    def _smiles_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size
        data = methods.paginated_data(f"{self.api}/users/my/content_smiles",
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

    def _comments_paginated(self, limit = None, next = None, prev = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self.api}/users/my/comments",
                                      "comments",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            objects.Comment(item["id"],
                            client = self,
                            data = item,
                            post = item["cid"],
                            root = item.get("root_comm_id"))
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

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

        response = methods.request("get",
                                   url,
                                   params = params,
                                   headers = self.sendbird_headers)

        paging = {"next": response["next"]}

        return {
            "paging":
            paging,
            "items": [
                objects.Chat(data["channel_url"], self, data = data)
                for data in response["channels"]
            ]
        }  # test chat

    def get(self, key, default = None):
        try:
            return self._object_data[key]
        except KeyError:
            return self.fresh._object_data.get(key, default)

    # private properties

    @property
    def _object_data(self):
        if self._update or self._object_data_payload is None:
            self._update = False

            if self.authenticated:
                self._object_data_payload = methods.request(
                    "get", f"{self.api}/account",
                    headers = self.headers)["data"]
            else:
                self._object_data_payload = {}

        return self._object_data_payload

    # public methods

    def login(self, email, password = "", force = False):
        """
        Authenticate with iFunny to get an API token.
        Will try to load saved account tokens (saved as plaintext json, indexed by `email_token`) if `force` is False

        :param email: Email associated with the account
        :param password: Password associated with the account
        :param force: Ignore saved Bearer tokens?

        :type email: str
        :type password: str
        :type force: bool

        :returns: self
        :rtype: Client
        """

        if self.authenticated:
            raise exceptions.AlreadyAuthenticated(
                f"This client instance already authenticated as {self.nick}")

        if not force and self._config.get(f"{email}_token"):
            self.__token = self._config[f"{email}_token"]

            try:
                methods.request("get",
                                f"{self.api}/account",
                                headers = self.headers)
                self.authenticated = True
                return self

            except exceptions.BadAPIResponse:
                self.__token = None

        data = {
            "grant_type": "password",
            "username": email,
            "password": password
        }

        self.__token = methods.request("post",
                                       f"{self.api}/oauth2/token",
                                       headers = self.headers,
                                       data = data)["access_token"]
        self.authenticated = True
        self._config[f"{email}_token"] = self.__token

        self._update_config()
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

    def post_image(self,
                   image_data,
                   tags = [],
                   visibility = "public",
                   type = "pic",
                   wait = False,
                   timeout = 15,
                   schedule = None):
        """
        Post an image to iFunny

        :param image_data: Binary image to post
        :param tags: List of searchable tags
        :param visibility: Visibility of the post on iFunny. Can be one of (``public``, ``subscribers``)
        :param type: type of content to post. Can be one of (``pic``, ``gif``)
        :param wait: wait for the post to be successfuly published?
        :param timeout: time to wait for a successful post
        :param schedule: timestamp to schedule the post for, or None for immediate

        :type image_data: bytes
        :type tags: list<str>
        :type visibility: str
        :type type: str
        :type wait: bool
        :type timeout: int
        :type schedule: int, or None

        :returns: Post if wait flag set (when posted)
        :rtype: Post, or None
        """
        if visibility not in {"public", "subscribers"}:
            raise ValueError(f"visibility cannot be {visibility}")

        data = {
            "type": type,
            "tags": json.dumps(tags),
            "visibility": visibility
        }

        if schedule:
            data["publish_at"] = int(schedule)

        files = {"image": image_data}

        id = methods.request("post",
                             f"{self.api}/content",
                             headers = self.headers,
                             data = data,
                             files = files,
                             codes = {202})["data"]["id"]
        posted = None

        if not wait:
            return

        while timeout * 2:
            posted = methods.request("get",
                                     f"{self.api}/tasks/{id}",
                                     headers = self.headers)["data"]

            if posted.get("result"):
                return objects.Post(posted["result"]["cid"], self)

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
                return self.commands.get(first[len(prefix):],
                                         commands.Defaults.default)(
                                             message, args)  # test chat

    def suggested_tags(self, query):
        """
        Tags suggested by ifunny for a query

        :param query: query for suggested tags

        :type query: str

        :returns: list of suggested tags and the number of memes with it
        :rty: list<tuple<str, int>>
        """
        params = {"q": str(query)}

        tags = methods.request("get",
                               f"{self.api}/tags/suggested",
                               params = params,
                               headers = self.headers)["data"]["tags"]["items"]

        return [(tag["tag"], tag["uses"]) for tag in tags]

    # sendbird methods

    def start_chat(self):
        """
        Start the chat websocket connection.

        :returns: this client's socket object
        :rtype: Socket

        :raises: Exception stating that the socket is already alive
        """
        if self.socket.active:
            raise exceptions.ChatAlreadyActive("Already started")

        return self.socket.start()  # test chat

    def stop_chat(self):
        """
        Stop the chat websocket connection.

        :returns: this client's socket object
        :rtype: Socket
        """
        return self.socket.stop()  # test chat

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
        files = {"file": file_data}

        data = {
            "thumbnail1": "780, 780",
            "thumbnail2": "320,320",
            "channel_url": chat.channel_url
        }

        return methods.request("post",
                               f"{self.sendbird_api}/storage/file",
                               headers = self.sendbird_headers,
                               files = files,
                               data = data)["url"]  # test chat

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
            self.commands[_name] = commands.Command(method, _name)

        return _inner  # test chat

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
            self.handler.events[_name] = handler.Event(method, _name)

        return _inner  # test chat

    # public properties

    @property
    def sendbird_headers(self):
        """
        Generate headers for a sendbird api call.
        If a messenger_token exists, it's added

        :returns: sendbird-ready headers
        :rtype: dict
        """
        _headers = {"User-Agent": "jand/3.096"}

        if self.messenger_token:
            _headers["Session-Key"] = self.messenger_token

        return _headers

    @property
    def headers(self):
        """
        Generate headers for iFunny requests dependant on authentication

        :returns: request-ready headers
        :rtype: dict
        """
        _headers = {
            "User-Agent": self._user_agent,
        }

        _headers[
            "Authorization"] = f"Bearer {self.__token}" if self.__token else f"Basic {self.basic_token}"

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

        if isinstance(_pref, str):
            _pref = [_pref]

        if isinstance(_pref, (set, tuple, list)):
            return set(_pref)

        raise TypeError(
            f"prefix must be str, iterable, or callable resulting in either. Not {type(_pref)}"
        )  # test chat

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

        raise TypeError(
            f"prefix must be str, iterable, or callable resulting in either. Not {type(_pref)}"
        )  # test chat

    @property
    def messenger_token(self):
        """
        Get the messenger_token used for sendbird api calls
        If a value is not stored in self.__messenger_token, one will be fetched from the client account data and stored

        :returns: messenger_token
        :rtype: str
        """
        if not self.__messenger_token:
            self.__messenger_token = self.fresh.get("messenger_token")

        return self.__messenger_token  ##

    @messenger_token.setter
    def messenger_token(self, value):
        self.__messenger_token = value  ##

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
    def home(self):
        """
        generator for a client's subscriptions feed (home feed).
        Each iteration will return the next home post, in decending order of date posted

        :returns: generator iterating the home feed
        :rtype: generator<Post>
        """
        return methods.paginated_generator(self._home_paginated)

    @property
    def smiles(self):
        """
        :returns: generator iterating posts that this client has smiled
        :rtype: generator<Post>
        """
        return methods.paginated_generator(self._smiles_paginated)

    @property
    def comments(self):
        """
        :returns: generator iterating comments that this client has left
        :rtype: generator<Comment>
        """
        return methods.paginated_generator(self._comments_paginated)

    @property
    def next_req_id(self):
        """
        Generate a new (sequential) sendbird websocket req_id in a thread safe way

        :returns: req_id
        :rtype: str
        """
        self._sendbird_lock.acquire()
        self.__sendbird_req_id += 1
        self._sendbird_lock.release()
        return self.__sendbird_req_id

    @property
    def user(self):
        """
        :returns: this client's user object
        :rtype: User
        """
        if not self.__user:
            self.__user = objects.User(self.id,
                                       client = self,
                                       paginated_size = self.paginated_size)

        return self.__user

    @property
    def unread_notifications_count(self):
        """
        :returns: number of unread notifications
        :rtype: int
        """
        return methods.request("get",
                               f"{self.api}/counters",
                               headers = self.headers)["data"][
                                   "news"]  # test with another account

    @property
    def nick(self):
        """
        :returns: this client's username (``nick`` name)
        :rtype: str
        """
        return self.get("nick")

    @property
    def email(self):
        """
        :returns: this client's associated email
        :rtype: str
        """
        return self.get("email")

    @property
    def id(self):
        """
        :returns: this client's unique id
        :rtype: str
        """
        if not self.__id:
            self.__id = self.get("id")

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

    # public generators

    @property
    def achievements(self):
        """
        :returns: generator iterating this clients achievements
        :rtype: generator<Achievement>
        """
        return methods.paginated_generator(self._achievements_paginated)

    @property
    def timeline(self):
        """
        Alias for ``self.user.timeline``
        """
        return self.user.timeline

    @property
    def chats(self):
        """
        generator for a Client's chats.
        Each iteration will return the next chat, in order of last message

        :returns: generator iterating through chats
        :rtype: generator<Chat>
        """
        if not self.messenger_token:
            raise exceptions.ChatNotActive(
                "Chat must be started at least once to get a session key")

        return methods.paginated_generator(self._chats_paginated)  # test chat
