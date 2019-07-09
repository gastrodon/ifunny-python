import json, os, requests, threading, time

from random import random
from hashlib import sha1
from base64 import b64encode

from ifunny.handler import Handler, Event
from ifunny.commands import Command, Defaults
from ifunny.sendbird import Socket
from ifunny.notifications import Notification
from ifunny.objects import User
from ifunny.utils import format_paginated, paginated_data, paginated_generator

class Client:
    """
    iFunny client used to do most things.

    :param handler: Websocket event handler
    :param socket: Websocket manager handling the chat connection
    :param trace: Trace boolean to send to the socket object
    :param prefix: Static string or callable prefix for chat commands
    :param paginated_size: Number of items to request in paginated methods

    :type handler: ifunny.handler.Handler
    :type socket: ifunny.sendbird.Socket
    :type trace: bool
    :type prefix: str or callable
    :type paginated_size: int
    """
    api = "https://api.ifunny.mobi/v4"
    sendbird_api = "https://api-us-1.sendbird.com/v3"
    __client_id = "MsOIJ39Q28"
    __client_secret = "PTDc3H8a)Vi=UYap"
    __user_agent = "iFunny/5.36(17704) Android/5.0.2 (samsung; SCH-R530U; samsung)"

    commands = {
        "help" : Defaults.help
    }

    def __init__(self, handler = Handler(), socket= Socket(), trace = False, prefix = {""}, paginated_size = 25):
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

        handler.client = self
        self.handler = handler

        socket.client = self
        self.socket = socket
        self.socket_trace = trace

        # own profile data
        self.__user = None
        self._account_data_payload = None
        self._update = False

        # cache file
        self.__cache_path = f"{os.path.dirname(os.path.realpath(__file__))}/ifunny_config.json"

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

    def _get_prop(self, key: str, force: bool = False):
        if not self.__account_data.get(key, None) or force:
            self._update = True

        return self.__account_data.get(key, None)

    def _notifications_paginated(self, limit: int = 30, prev: str = None, next: str = None):
        data = paginated_data(
            f"{self.api}/news/my", "news", self.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Notification(item, self) for item in data["items"]]

        return format_paginated(data, items)

    # private properties

    @property
    def __sendbird_headers(self):
        """
        Generate headers for a sendbird api call

        returns
            dict
        """
        _headers = {}

        if self.socket.connected:
            _headers["Session-Key"] = self.sendbird_session_key

        return _headers

    @property
    def __login_token(self):
        """
        Generate or load from config a Basic auth token

        returns
            string
        """
        if self.__config.get("login_token"):
            return self.__config["login_token"]

        hex_string = os.urandom(32).hex().upper()
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
            self._account_data_payload = requests.get(f"{self.api}/account", headers = self.headers).json()["data"]

        return self._account_data_payload

    # public methods

    def login(self, email, password, force = False):
        """
        Authenticate with iFunny to get an API token.
        Will try to load saved account tokens (saved as plaintext json, indexed by `email_token`) if `force` is False

        :param email: Email associated with the account
        :param password: Password associated with the account
        :param force: True to ignore saved Bearer tokens

        :type email: str
        :type password: str
        :type force: bool
        """

        if self.authenticated:
            raise Exception(f"Already logged in as {self.nick}")

        if not force and self.__config.get(f"{email}_token"):
            self.__token = self.__config[f"{email}_token"]
            response = requests.get(f"{self.api}/account", headers = self.headers)

            if response.status_code == 200:
                self.authenticated = True
                return

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
            raise Exception(response.text)

        self.__token = response.json()["access_token"]
        self.authenticated = True
        self.__config[f"{email}_token"] = self.__token

        self.__update_config()

    def post_image(self, image_data: bytes, tags: list = [], visibility: str = "public"):
        """
        Post an image to iFunny

        :param image_data: Binary image to post
        :param tags: List of searchable tags
        :param visibility: Visibility of the post on iFunny

        :type image_data: bytes
        :type tags: list<str>
        :type visibility: str

        :returns: True if successfuly posted (POST response is 202) else False
        :rtype: bool
        """
        data = {
            "type": "pic",
            "tags": json.dumps(tags),
            "visibility": visibility
        }

        files = {
            "image": image_data
        }

        response = requests.post(f"{self.api}/content", headers = self.headers, data = data, files = files)
        return response.status_code == 202

    def resolve_command(self, ctx):
        """
        Find and call a command called from a message

        :param ctx: Message content

        :type ctx: MessageContext
        """
        parsed = ctx.message.split(" ")
        first, args = parsed[0], parsed[1:]

        for prefix in self.prefix:
            if first.startswith(prefix):
                cmd = self.commands.get(first[len(prefix):], Defaults.default)(ctx, args)
                cmd(ctx, args)

    # sendbird methods

    def start_chat(self):
        """
        Start the chat websocket connection

        :returns: this client's socket object
        :rtype: Socket

        :raises: Exception stating that the socket is already alive
        """
        if self.socket.active:
            raise Exception("Already started")

        if not self.messenger_token:
            self.messenger_token = self.__account_data["messenger_token"]

        return self.socket.start()

    def sendbird_upload(self, channel, file_data):
        """
        Upload an image to sendbird for a specific channel

        :param channel: channel to upload the file for
        :param file_data: binary file to upload

        :type channel: ifunny.objects.Channel
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
            "channel_url"   : channel.url
        }

        response = requests.post(f"{self.sendbird_api}/storage/file", headers = self.__sendbird_headers, files = files, data = data)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()["url"]

    # public decorators

    def command(self, name = None):
        """
        Decorator to add a command, callable in chat with the format ``{prefix}{command}``
        Commands must take two arguments, which are set as the MessageContext and list<str> of space-separated words in the message (excluding the command) respectively::

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
    def headers(self):
        """
        Generate headers for iFunny requests dependant on authentication

        :returns: request-ready headers
        :rtype: dict
        """
        _headers = {
            "User-Agent": self.__user_agent
        }

        if self.__token:
            _headers["Authorization"] = f"Bearer {self.__token}"

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
        self.__sendbird__req_id += 1
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
        :returns: this client's username (``nick``\ name)
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

    # public generators

    @property
    def notifications(self):
        """
        Generator for a client's notifications.
        Each iteration will return the next notification, in decending order of date recieved

        :returns: generator iterating through notifications
        :rtype: Generator<Notification>
        """
        return paginated_generator(self._notifications_paginated)
