import json, time, random, requests
from ifunny.utils import determine_mime, invalid_type, format_paginated, paginated_data, paginated_generator

class ObjectBase:
    def __init__(self, id, client, data = None, post = None, root = None, update_interval = 30):
        self.client = client
        self.id = id

        self._account_data_payload = data
        self._updated = time.time()
        self._update_interval = update_interval

        self._url = None
        self._post = post
        self._root = root

    def _get_prop(self, key):
        if not self._account_data.get(key, None):
            self._updated = 0

        return self._account_data.get(key, None)

    def _flush_cache(self):
        self._account_data_payload = None

    @property
    def _account_data(self):
        if time.time() - self._updated > self._update_interval or self._account_data_payload is None:
            self._updated = time.time()
            self._account_data_payload = requests.get(self._url, headers = self.client.headers).json()["data"]

        return self._account_data_payload

class User(ObjectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chat_url = None
        self._url = f"{self.client.api}/users/{self.id}"

    def __repr__(self):
        return self.nick

    def __eq__(self, other):
        return self.id == other

    # public methods

    # paginated data

    def timeline_paginated(self, limit = 25, prev = None, next = None):
        data = paginated_data(
            f"{self.client.api}/timelines/users/{self.id}", "content", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    def subscribers_paginated(self, limit = 25, prev = None, next = None):
        data = paginated_data(
            f"{self._url}/subscribers", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    def subscriptions_paginated(self, limit = 25, prev = None, next = None):
        data = paginated_data(
            f"{self._url}/subscriptions", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    # actions

    def subscribe(self):
        response = requests.put(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    def unsubscribe(self):
        response = requests.delete(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    def block(self, type = "user"):
        valid = ["user", "installation"]

        if type not in valid:
            raise invalid_type("type", type, valid)

        params = {
            "type": type
        }

        response = requests.put(f"{self.client.api}/users/my/blocked/{self.id}", params = params, headers = self.client.headers)

        if response.status_code != 200:
            if response.json().get("error") == "already_blocked":
                return False

            raise Exception(response.text)

        return True

    def unblock(self):
        params = {
            "type": "user"
        }

        response = requests.delete(f"{self.client.api}/users/my/blocked/{self.id}", params = params, headers = self.client.headers)

        if response.status_code != 200:
            if response.json().get("error") == "not_blocked":
                return False

            raise Exception(response.text)

        return True

    def report(self, type):
        valid = ["hate", "nude", "spam", "target", "harm"]

        if type not in valid:
            raise invalid_type("type", type, valid)

        params = {
            "type": type
        }

        response = requests.put(f"{self._url}/abuses", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    # public generators

    @property
    def timeline(self):
        for i in paginated_generator(self.timeline_paginated):
            yield i

    @property
    def subscribers(self):
        for i in paginated_generator(self.subscribers_paginated):
            yield i

    @property
    def subscriptions(self):
        for i in paginated_generator(self.subscriptions_paginated):
            yield i

    # public properties

    # authentication independant attributes

    @property
    def nick(self):
        return self._get_prop("nick")

    @property
    def about(self):
        return self._get_prop("about")

    @property
    def posts(self):
        self._flush_cache()
        return self._get_prop("num")["featured"]

    @property
    def featured(self):
        self._flush_cache()
        return self._get_prop("num")["featured"]

    @property
    def total_smiles(self):
        self._flush_cache()
        return self._get_prop("num")["total_smiles"]

    @property
    def subscriber_count(self):
        return self._get_prop("num")["subscribers"]

    @property
    def subscription_count(self):
        return self._get_prop("num")["subscriptions"]

    @property
    def is_verified(self):
        return self._get_prop("is_verified")

    @property
    def is_banned(self):
        return self._get_prop("is_banned")

    @property
    def is_deleted(self):
        return self._get_prop("is_deleted")

    @property
    def days(self):
        return self._get_prop("meme_experience")["days"]

    @property
    def rank(self):
        return self._get_prop("meme_experience")["rank"]

    @property
    def nick_color(self):
        return self._get_prop("nick_color")

    @property
    def chat_privacy(self):
        return self._get_prop("messaging_privacy_status")

    @property
    def chat_url(self):
        if not self._chat_url:
            data = {
                "chat_type": "chat",
                "users": self.id
            }

            response = requests.post(f"{self.client.api}/chats", headers = self.client.headers, data = data)
            self._chat_url = (response.url, data, response.text)

        return self._chat_url

    # authentication dependant attributes

    @property
    def blocked(self):
        return self._get_prop("is_blocked")

    @property
    def blocking_me(self):
        return self._get_prop("are_you_blocked")

    @property
    def can_chat(self):
        return self._get_prop("is_available_for_chat")

    @property
    def notification_updates(self):
        return self._get_prop("is_subscribed_to_updates")

    @property
    def is_subscribed(self):
        return self._get_prop("is_in_subscribers")

    @property
    def is_subscription(self):
        return self._get_prop("is_in_subscriptions")

class Post(ObjectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = f"{self.client.api}/content/{self.id}"

    def __eq__(self, other):
        return self.id == other

    # public methods

    # paginated data

    def smiles_paginated(self, limit = 25, prev = None, next = None):
        data = paginated_data(
            f"{self._url}/smiles", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    def comments_paginated(self, limit = 25, prev = None, next = None):
        data = paginated_data(
            f"{self._url}/comments", "comments", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self.client, data = item, post = self) for item in data["items"]]

        return format_paginated(data, items)

    # public generators

    @property
    def smiles(self):
        for i in paginated_generator(self.smiles_paginated):
            yield i

    @property
    def comments():
        for i in paginated_generator(self.comments_paginated):
            yield i

    # public properties

    # authentication independant attributes

    @property
    def smile_count(self):
        return self._get_prop("num")["smiles"]

    @property
    def unsmile_count(self):
        return self._get_prop("num")["unsmiles"]

    @property
    def guest_smile_count(self):
        return self._get_prop("num")["guest_smiles"]

    @property
    def comment_count(self):
        return self._get_prop("num")["comments"]

    @property
    def views(self):
        return self._get_prop("num")["views"]

    @property
    def republish_count(self):
        return self._get_prop("num")["republished"]

    @property
    def shares(self):
        return self._get_prop("num")["shares"]

    @property
    def creator(self):
        data = self._get_prop("creator")
        return User(data["id"], self.client, data = data)

    @property
    def source(self):
        return self._get_prop("source")

    @property
    def is_original(self):
        return self.source is None

    @property
    def is_feautured(self):
        return self._get_prop("is_feautured")

    @property
    def is_pinned(self):
        return self._get_prop("is_pinned")

    @property
    def is_abused(self):
        return self._get_prop("is_abused")

    @property
    def type(self):
        return self._get_prop("type")

    @property
    def tags(self):
        return self._get_prop("tags")

    @property
    def visibility(self):
        return self._get_prop("visibility")

    @property
    def state(self):
        return self._get_prop("state")

    @property
    def boostable(self):
        return self._get_prop("can_be_boosted")

    @property
    def created_at(self):
        return self._get_prop("date_created")

    @property
    def published_at(self):
        return self._get_prop("published_at")

    @property
    def content_url(self):
        return self._get_prop("url")

    @property
    def content(self):
        return requests.get(self.content_url).content

    # authentication dependant attributes

    @property
    def is_republished(self):
        return self._get_prop("is_republished")

    @property
    def smiled(self):
        return self._get_prop("is_smiled")

    @property
    def unsmiled(self):
        return self._get_prop("is_unsmiled")

class Comment(ObjectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._post == None and self._account_data_payload["cid"] == None:
            raise Exception("This needs a post")

        self._url = f"{self.client.api}/content/{self.cid}/comments" if not self._root else f"{self.client.api}/content/{self.cid}/comments/{self._root}/replies"

    def __repr__(self):
        return self.content

    def __eq__(self, other):
        return self.id == other

    @property
    def _account_data(self):
        if time.time() - self._updated > self._update_interval or self._account_data_payload is None:
            self._updated = time.time()

            params = {
            "limit":    1,
            "show":     self.id
            }

            key = "replies" if self._root else "comments"
            post_comments = requests.get(self._url, headers = self.client.headers).json()["data"][key]["items"]
            mine = [item for item in post_comments if item["id"] == self.id]

            if not len(mine):
                self._account_data_payload = {"is_deleted": True}
            else:
                self._account_data_payload = mine[0]

        return self._account_data_payload

    # public properties

    def replies_paginated(self, limit = 25, prev = None, next = None):
        data = paginated_data(
            f"{self._url}/{self.id}/replies", "replies", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self.client, data = item, post = self.cid, root = self.id) for item in data["items"]]

        return format_paginated(data, items)

    # public generators

    @property
    def replies(self):
        for i in paginated_generator(self.replies_paginated):
            yield i

    # public properties

    # authentication independant properties

    @property
    def content(self):
        value = self._get_prop("text")
        return value if value else ""

    @property
    def cid(self):
        if type(self._post) is str:
            self._post = Post(self._post, self.client)

        if self._post:
            return self._post.id

        if not self.__cid:
            self.__cid = self._get_prop("cid")

        return self.__cid

    @property
    def state(self):
        return self._get_prop("state")

    @property
    def author(self):
        data = self._get_prop("user")
        return User(data["id"], self.client, data = data)

    @property
    def post(self):
        return Post(self.cid, self.client)

    @property
    def root(self):
        if self.is_root:
            return None

        return Comment(self._get_prop("root_comm_id"), self.client, post = self.cid)

    @property
    def root(self):
        if self.is_root:
            return None

        return Comment(self._get_prop("root_comm_id"), self.client, post = self.cid)

    @property
    def smile_count(self):
        return self._get_prop("num")["smiles"]

    @property
    def unsmile_count(self):
        return self._get_prop("num")["unsmiles"]

    @property
    def reply_count(self):
        return self._get_prop("num")["replies"]

    @property
    def created_at(self):
        self._get_prop("date")

    @property
    def depth(self):
        if self.is_root:
            return 0

        return self._get_prop("depth")

    @property
    def is_root(self):
        return not self._get_prop("is_reply")

    @property
    def is_deleted(self):
        value = self._get_prop("is_deleted")
        return value if value else False

    @property
    def is_edited(self):
        return self._get_prop("is_edited")

    @property
    def attached_post(self):
        data = self._get_prop("attachments")["content"]

        if len(data) == 0:
            return None

        return Post(data[0]["id"], self.client, data = data[0])

    @property
    def mentioned_users(self):
        data = self._get_prop("attachments")["mention_user"]

        if len(data) == 0:
            return []

        return [User(item["user_id"], self.client) for item in data]

    # authentication dependant properties

    @property
    def is_smiled(self):
        return self._get_prop("is_smiled")

    @property
    def is_unsmiled(self):
        return self._get_prop("is_unsmiled")

class ChatChannel:
    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.sendbird_url = data["channel_url"]
        self.id = data["channel_id"]
        self.type = data["channel_type"]

class MessageContext:
    def __init__(self, client, data):
        self.client = client
        self.socket = self.client.socket
        self.commands = self.client.commands
        self.channel_url = data["channel_url"]
        self.message = data["message"]

    def send(self, message):
        response_data = {
            "channel_url"   : self.channel_url,
            "message"       : message
        }

        return self.socket.send(f"MESG{json.dumps(response_data, separators = (',', ':'))}\n")


    def send_file_url(self, image_url, width = 780, height = 780):
        lower_ratio = min([width / height, height / width])
        type = "tall" if height >= width else "wide"
        mime = determine_mime(image_url)

        response_data = {
            "channel_url"   : self.channel_url,
            "name"          : f"botimage",
            "req_id"        : str(int(round(time.time() * 1000))),
            "type"          : mime,
            "url"           : image_url,
            "thumbnails"    : [
                {
                    "url"           : image_url,
                    "real_height"   : int(780 if type == "tall" else 780 * lower_ratio),
                    "real_width"    : int(780 if type == "wide" else 780 * lower_ratio),
                    "height"        : width,
                    "width"         : height,
                }
            ]
        }

        return self.socket.send(f"FILE{json.dumps(response_data, separators = (',', ':'))}\n")

    @property
    def prefix(self):
        return self.client.prefix
