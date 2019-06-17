import praw, requests, json, os, base64, base64, hashlib
from time import time, sleep
from random import random
from threading import Lock
from os import urandom
from hashlib import sha1
from base64 import b64encode

from ifunny.sendbird import Socket
from ifunny.notifications import resolve_notification
from ifunny.handler import Handler


class Client:
    def __init__(self, handler = Handler, socket = Socket, trace = False, prefix = "-"):
        self.api = "https://api.ifunny.mobi/v4"
        self.id = None
        self.token = None
        self.authenticated = False

        self.socket = socket(self)
        self.trace = trace
        self.handler = handler(self)
        self.commands = Commands(self, prefix)

        self.__login_token = self.__generate_login_token()
        self.__sendbird_req_id = int(time() * 1000 + random() * 1000000)

        self.__sendbird_req_lock = Lock()

        self.recently_posted = []
        self._last_read_hash = None

        # initialize ifunny account info
        self.id = None
        self.messenger_token = None
        self.nick = None
        self.emial = None
        self.banned = None
        self.verified = None
        self.deleted = None
        self.subs = None
        self.posts = None
        self.days = None
        self.featured = None
        self.smiles = None

        with open("config.json") as stream:
            self.__config = json.load(stream)

    def login(self, email, password, force = False):
        if not force:
            if self.__config.get(f"{email}_token"):
                self.token = self.__config[f"{email}_token"]
                self.authenticated = True
                self.update_profile()
                return

        headers = {
            "Authorization": f"Basic {self.__login_token}"
        }

        data = {
            "grant_type": "password",
            "username": email,
            "password": password
        }

        response = requests.post(f"https://api.ifunny.mobi/v4/oauth2/token", headers = headers, data = data)

        if response.status_code == 403:
            sleep(10)
            response = requests.post(f"https://api.ifunny.mobi/v4/oauth2/token", headers = headers, data = data)

        if response.status_code != 200:
            raise Exception(response.text)

        self.token = response.json()["access_token"]
        self.authenticated = True
        self.__config[f"{email}_token"] = self.token

        with open("config.json", "w") as stream:
            json.dump(self.__config, stream)

        self.update_profile()

    @property
    def headers(self):
        _headers = {}

        if self.authenticated:
            _headers["Authorization"] = f"Bearer {self.token}"

        return _headers

    def get_notifications(self, limit = 30, types = None, prev = None, next = None):
        headers = self.headers

        params = {
            "limit": limit
        }

        if next:
            params["next"] = next

        elif prev:
            params["prev"] = prev

        response = requests.get(f"{self.api}/news/my", headers = headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        items = [resolve_notification(item, self) for item in response.json()["data"]["news"]["items"]]
        paging = response.json()["data"]["news"]["paging"]

        if types:
            items = [item for item in items if item.type in types]

        return {
            "items": items,
            "paging": paging
        }

    def __generate_login_token(self, path = "config.json"):
        with open(path, "r") as stream:
            config = json.load(stream)

        if config.get("login_token"):
            return config["login_token"]

        client_id = config["client_id"]
        client_secret = config["client_secret"]

        hex_string = urandom(32).hex().upper()
        hex_id = f"{hex_string}_{client_id}"
        hash_decoded = f"{hex_string}:{client_id}:{client_secret}"
        hash_encoded = sha1(hash_decoded.encode('utf-8')).hexdigest()
        config["login_token"] = b64encode(bytes(f"{hex_id}:{hash_encoded}", 'utf-8')).decode()


        with open(path, "w") as stream:
            json.dump(config, stream)

        return config["login_token"]

    # Profile Stuff

    def update_profile(self):
        if not self.authenticated:
            raise Exception("Not logged in")

        data = self.fetch_account_data()
        self.id = data["id"]
        self.messenger_token = data["messenger_token"]
        self.nick = data["nick"]
        self.emial = data["email"]
        self.banned = data["is_banned"]
        self.verified = data["is_verified"]
        self.deleted = data["is_deleted"]
        self.subs = data["num"]["subscribers"]
        self.posts = data["num"]["total_posts"]
        self.days = data["num"]["created"]
        self.featured = data["num"]["featured"]
        self.smiles = data["num"]["total_smiles"]

    def fetch_account_data(self):
        headers = self.headers
        return requests.get(f"{self.api}/account", headers = headers).json()["data"]

    @property
    def unread_notifications(self):
        headers = self.headers
        unread = []
        page_next = None

        response = requests.get(f"{self.api}/counters", headers = headers)

        if response.status_code != 200:
            raise Exception(response.text)

            count = response.json()["data"]["news"]

            if not count:
                return []

                while len(unread) < count:
                    fetched_notifs = self.get_notifications(next = page_next)
                    unread = [*unread, *fetched_notifs["items"]]
                    page_next = fetched_notifs["paging"]["cursors"]["next"] if fetched_notifs["paging"]["hasNext"] else None

                    if not page_next:
                        break

                        return unread[:count]

    # Posting

    def post_image(self, image_data, tags = []):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        data = {
            "type": "pic",
            "tags": json.dumps(tags),
            "visibility": "public"
        }

        files = {
            "image": image_data
        }

        response = requests.post(f"{self.api}/content", headers = headers, data = data, files = files)

        return response.status_code

    # Chat
    def start_chat(self):
        self.socket.start()

    @property
    def sendbird_req_id(self):
        self.__sendbird_req_lock.acquire()
        self.__sendbird_req_id += 1
        self.__sendbird_req_lock.release()
        return self.__sendbird_req_id

    @sendbird_req_id.setter
    def sendbird_req_id(self, value):
        value = int(value)
        self.__sendbird_req_lock.acquire()
        self.__sendbird_req_id = value
        self.__sendbird_req_lock.release()
        return self.__sendbird_req_id

class Commands:
    def __init__(self, client, prefix):
        self.client = client
        self.table = {
            "help": self._help
        }
        self.__prefix = prefix

    def _help(self, ctx, args):
        ctx.send(f"These commands are available:\n{', '.join(self.table.keys())}")

    def _default(self, ctx, args):
        return

    def get_prefix(self, ctx):
        if isinstance(self.__prefix, str):
            return self.__prefix

        return self.__prefix(ctx)


    def add(self, name = None):
        def _inside(method):
            c_name = name if name else method.__name__
            self.table[c_name] = method

        return _inside

    def resolve_execute(self, ctx):
        prefix = ctx.prefix
        first = ctx.message.split(" ")[0]
        args = ctx.message.split(" ")[1:]
        if not first.startswith(prefix):
            return None

        exec = self.table.get(first[len(prefix):], self._default)
        return exec(ctx, args)
