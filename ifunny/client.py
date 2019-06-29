import json, os, requests, threading

from random import random
from hashlib import sha1
from base64 import b64encode
from time import time, sleep

from ifunny.handler import Handler
from ifunny.commands import Command, Defaults
from ifunny.sendbird import Socket
from ifunny.notifications import resolve_notification

class Client:
    api = "https://api.ifunny.mobi/v4"
    sendbird_api = "https://api-us-1.sendbird.com/v3"
    __client_id = "MsOIJ39Q28"
    __client_secret = "PTDc3H8a)Vi=UYap"

    commands = {
        "help" : Defaults.help
    }

    def __init__(self, handler = Handler(), socket = Socket(), trace = False, prefix = ""):

        # command
        self.__prefix = prefix

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
        self.__sendbird_req_id = int(time() * 1000 + random() * 1000000)

        # attatched classes
        handler.client = self
        self.handler = handler

        socket.client = self
        self.socket = socket
        self.socket_trace = trace

        # cache file
        self.__cache_path = f"{os.path.dirname(os.path.realpath(__file__))}/ifunny_config.json"

        try:
            with open(self.__cache_path) as stream:
                self.__config = json.load(stream)

        except (FileNotFoundError):
            self.__config = {}
            self.__update_config()

    # private properties

    @property
    def __headers(self):
        _headers = {}

        if self.__token:
            _headers["Authorization"] = f"Bearer {self.__token}"

        return _headers

    @property
    def __sendbird_headers(self):
        _headers = {}

        if self.socket.connected:
            _headers["Session-Key"] = self.sendbird_session_key

        return _headers

    @property
    def __login_token(self):
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
        return requests.get(f"{self.api}/account", headers = self.__headers).json()["data"]

    # public properties

    @property
    def prefix(self):
        if callable(self.__prefix):
            return self.__prefix()

        if isinstance(self.__prefix, str):
            return self.__prefix

        raise Exception(f"prefix must be callable or str, not {type(self.__prefix)}")

    @property
    def messenger_token(self):
        if not self.__messenger_token:
            self.__messenger_token = self.__account_data["messenger_token"]

        return self.__messenger_token

    @property
    def unread_notifications(self):
        unread = []
        page_next = None

        response = requests.get(f"{self.api}/counters", headers = self.__headers)

        if response.status_code != 200:
            raise Exception(response.text)

        count = response.json()["data"]["news"]

        if not count:
            return unread

        while len(unread) < count:
            fetched = self.get_notifications(next = page_next)
            unread = [*unread, *fetched["items"]]
            page_next = fetched["paging"]["next"]

            if not page_next:
                break

        return unread[:count]

    @property
    def next_req_id(self):
        self.__sendbird_lock.acquire()
        self.__sendbird__req_id += 1
        self.__sendbird_lock.release()
        return self.__sendbird_req_id

    # private methods

    def __update_config(self):
        self.__config_lock.acquire()
        with open(self.__cache_path, "w") as stream:
            json.dump(self.__config, stream)
        self.__config_lock.release()

    # public methods

    def get_notifications(self, limit = 30, types = None, prev = None, next = None):
        params = {
            "limit" : limit
        }

        if next:
            params["next"] = next

        elif prev:
            params["prev"] = prev

        response = requests.get(f"{self.api}/news/my", headers = self.__headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        parsed = response.json()["data"]["news"]
        items = [resolve_notification(self, item) for item in parsed["items"]]

        if types:
            items = [item for item in items if item.type in types]

        paging = {
            "prev": parsed["paging"]["cursors"]["prev"] if parsed["paging"]["hasPrev"] else None,
            "next": parsed["paging"]["cursors"]["next"] if parsed["paging"]["hasNext"] else None
        }

        return {
            "items": items,
            "paging": paging
        }

    def login(self, email, password, force = False):
        if not force and self.__config.get(f"{email}_token"):
            self.__token = self.__config[f"{email}_token"]
            response = requests.get(f"{self.api}/account", headers = self.__headers)

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
            sleep(10)
            response = requests.post(f"{self.api}/oauth2/token", headers = headers, data = data)

        if response.status_code != 200:
            raise Exception(response.text)

        self.__token = response.json()["access_token"]
        self.authenticated = True
        self.__config[f"{email}_token"] = self.__token

        self.__update_config()

    def post_image(self, image_data, tags = [], visibility = "public"):
        data = {
            "type": "pic",
            "tags": json.dumps(tags),
            "visibility": visibility
        }

        files = {
            "image": image_data
        }

        response = requests.post(f"{self.api}/content", headers = self.__headers, data = data, files = files)
        return response.status_code

    def resolve_command(self, ctx):
        parsed = ctx.message.split(" ")
        first, args = parsed[0], parsed[1:]

        if not first.startswith(self.prefix):
            return

        cmd = self.commands.get(first[len(self.prefix):], Defaults.default)
        cmd.execute(ctx, args)

    # public decorators

    def command(self, name = None):
        def _inner(method):
            _name = name if name else method.__name__
            self.commands[_name] = Command(method, _name)

        return _inner

    # sendbird methods

    def start_chat(self):
        if not self.messenger_token:
            self.messenger_token = self.__account_data["messenger_token"]

        return self.socket.start()

    # sendbird coroutines

    def sendbird_upload(self, channel_url, file_data):
        files = {
            "file": file_data
        }

        data = {
            "thumbnail1"    : "780, 780",
            "thumbnail2"    : "320,320",
            "channel_url"   : channel_url
        }

        response = requests.post(f"{self.sendbird_api}/storage/file", headers = self.__sendbird_headers, files = files, data = data)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()["url"]

    # account info properties

    @property
    def nick(self):
        return self.__account_data["nick"]

    @property
    def email(self):
        return self.__account_data["email"]

    @property
    def id(self):
        if not self.__id:
            self.__id = self.__account_data["id"]

        return self.__id
