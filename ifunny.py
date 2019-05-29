import praw, requests, json, os, base64, base64, hashlib
from sendbird import Socket
from notifications import resolve_notification
from os import urandom
from random import randrange
from time import sleep
from hashlib import sha1
from base64 import b64encode

class Poster:
    def __init__(self):
        self.api = "https://api.ifunny.mobi/v4"
        self.id = None
        self.token = None
        self.authenticated = False
        self.socket = Socket(self)

        self.__login_token = self.__generate_login_token()

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
            if self.__config.get(f"{email}_bearer"):
                self.token = self.__config[f"{email}_bearer"]
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
        _headers = {
            "User-Agent": "iFunny/5.33.1(17680) Android/5.0.2 (samsung; SCH-R530U; samsung)"
        }

        if self.authenticated:
            _headers["Authorization"] = f"Bearer {self.token}"

        return _headers

    @property
    def account(self):
        headers = self.headers
        return requests.get(f"{self.api}/account", headers = headers).json()["data"]

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

    def update_profile(self):
        if not self.authenticated:
            raise Exception("Not logged in")

        data = self.account
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

    def post_image(self, image_data, tags = []):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "iFunny/5.33.1(17680) Android/5.0.2 (samsung; SCH-R530U; samsung)"
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
