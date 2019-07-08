import json, time, random, requests
from ifunny.utils import determine_mime, invalid_type, format_paginated, paginated_data, paginated_generator

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
    def __init__(self, id, client, data = None, paginated_size = 30):
        self.client = client
        self.id = id

        self._account_data_payload = data
        self._update = data is None

        self._url = None

        self.paginated_size = paginated_size

    def _get_prop(self, key, default = None, force = False):
        if not self._account_data.get(key, None) or force:
            self._update = True

        return self._account_data.get(key, default)

    @property
    def _account_data(self):
        if self._update or self._account_data_payload is None:
            self._update = False
            response = requests.get(self._url, headers = self.client.headers)
            if response.status_code == 403:
                self._account_data_payload = {}
                return self._account_data_payload
            try:
                self._account_data_payload = response.json()["data"]
            except KeyError:
                raise Exception(response.text)

        return self._account_data_payload

    @property
    def fresh(self):
        """
        Return self after setting the update flag

        :returns: self
        :rtype: Subclass of ObjectMixin
        """
        self._update = True
        return self

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
    def __init__(self, id, client, data = None, paginated_size = 30, post = None, root = None):
        super().__init__(id, client, data = data, paginated_size = paginated_size)
        self._post = post
        self._root = root

    @property
    def _account_data(self):
        if self._update or self._account_data_payload is None:
            self._update = False

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

class User(ObjectMixin):
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

    def _timeline_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size
        limit = min(100, limit)

        data = paginated_data(
            f"{self.client.api}/timelines/users/{self.id}", "content", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    def _subscribers_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/subscribers", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    def _subscriptions_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/subscriptions", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    # actions

    def subscribe(self):
        """
        Subscribe to a user

        :returns: self for chaining methods
        :rtype: User
        """
        response = requests.put(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise Exception(response.text)

        return self

    def unsubscribe(self):
        """
        Unsubscribe from a user

        :returns: self for chaining
        :rtype: User
        """
        response = requests.delete(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    def block(self, type = "user"):
        """
        Block a user, either by account or device

        :param type: type of block. user blocks a user, installation blocks all users tied to a device

        :type type: str

        :returns: self for chaining

        :rtype: User
        """
        valid = ["user", "installation"]

        if type not in valid:
            raise invalid_type("type", type, valid)

        params = {
            "type": type
        }

        response = requests.put(f"{self.client.api}/users/my/blocked/{self.id}", params = params, headers = self.client.headers)

        if response.status_code != 200:
            if response.json().get("error") == "already_blocked":
                return self

            raise Exception(response.text)

        return self

    def unblock(self):
        """
        Unblock a user

        :returns: self for chaining
        :rtype: User
        """
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
        """
        Report a user

        :param type: reason for report
            hate   -> hate speech
            nude   -> nudity
            spam   -> spam posting
            target -> targeted harrassment
            harm   -> encouraging harm or violence

        :type type: str

        :returns: self for chaining

        :rtype: User
        """
        valid = ["hate", "nude", "spam", "target", "harm"]

        if type not in valid:
            raise invalid_type("type", type, valid)

        params = {
            "type": type
        }

        response = requests.put(f"{self._url}/abuses", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        return self

    # public generators

    @property
    def timeline(self):
        """
        :returns: Generator iterating user posts

        :rtype: Generator<Post>
        """
        return paginated_generator(self._timeline_paginated)

    @property
    def subscribers(self):
        """
        :returns: Generator iterating user subscipbers

        :rtype: Generator<User>
        """
        return paginated_generator(self._subscribers_paginated)

    @property
    def subscriptions(self):
        """
        :returns: Generator iterating user subscriptions

        :rtype: Generator<User>
        """
        return paginated_generator(self._subscriptions_paginated)

    # public properties

    # authentication independant attributes

    @property
    def nick(self):
        """
        :retunrs: this users nickname
        :rtype: str
        """
        return self._get_prop("nick")

    @property
    def about(self):
        """
        :retunrs: this users about section
        :rtype: str
        """
        return self._get_prop("about")

    @property
    def posts(self):
        """
        :retunrs: this users post count
        :rtype: int
        """
        return self._get_prop("num")["featured"]

    @property
    def featured(self):
        """
        :retunrs: this users feature count
        :rtype: int
        """
        return self._get_prop("num")["featured"]

    @property
    def total_smiles(self):
        """
        :retunrs: this users smile count
        :rtype: int
        """
        return self._get_prop("num")["total_smiles"]

    @property
    def subscriber_count(self):
        """
        :retunrs: this users subscriber count
        :rtype: int
        """
        return self._get_prop("num")["subscribers"]

    @property
    def subscription_count(self):
        """
        :retunrs: this users subscruption count
        :rtype: int
        """
        return self._get_prop("num")["subscriptions"]

    @property
    def is_verified(self):
        """
        :retunrs: True if this user is verified
        :rtype: bool
        """
        return self._get_prop("is_verified")

    @property
    def is_banned(self):
        """
        :retunrs: True if this user is banned
        :rtype: bool
        """
        return self._get_prop("is_banned")

    @property
    def is_deleted(self):
        """
        :retunrs: True if this user is deleted
        :rtype: bool
        """
        return self._get_prop("is_deleted")

    @property
    def days(self):
        """
        :returns: this users active days count
        :rtype: int
        """
        return self._get_prop("meme_experience")["days"]

    @property
    def rank(self):
        """
        :retunrs: this users meme experience rank
        :rtype: str
        """
        return self._get_prop("meme_experience")["rank"]

    @property
    def nick_color(self):
        """
        :retunrs: this users nickname color
        :rtype: str
        """
        return self._get_prop("nick_color")

    @property
    def chat_privacy(self):
        """
        :retunrs: this users chat privacy settings (privacy, public, subscribers)
        :rtype: str
        """
        return self._get_prop("messaging_privacy_status")

    @property
    def chat_url(self):
        """
        :retunrs: this users chat url
        :rtype: str
        """
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
        """
        :retunrs: True if this user is blocked the client
        :rtype: bool
        """
        return self._get_prop("is_blocked")

    @property
    def blocking_me(self):
        """
        :retunrs: True if this user is blocking the client
        :rtype: bool
        """
        return self._get_prop("are_you_blocked")

    @property
    def can_chat(self):
        """
        :retunrs: True if this user can chat with the client
        :rtype: bool
        """
        return self._get_prop("is_available_for_chat", False)

    @property
    def subscribed_to_updates(self):
        """
        :retunrs: True if this user is subscribed to notification updates
        :rtype: bool
        """
        return self._get_prop("is_subscribed_to_updates", False)

    @property
    def is_subscribed(self):
        """
        :retunrs: True if this user is subscribed to the client
        :rtype: bool
        """
        return self._get_prop("is_in_subscribers", False)

    @property
    def is_subscription(self):
        """
        :retunrs: True if this client is subscribed to the user
        :rtype: bool
        """
        return self._get_prop("is_in_subscriptions", False)

class Post(ObjectMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = f"{self.client.api}/content/{self.id}"

    def __eq__(self, other):
        return self.id == other

    # public methods

    # paginated data

    def _smiles_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/smiles", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return format_paginated(data, items)

    def _comments_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/comments", "comments", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self.client, data = item, post = self) for item in data["items"]]

        return format_paginated(data, items)

    # public generators

    @property
    def smiles(self):
        return paginated_generator(self._smiles_paginated)

    @property
    def comments(self):
        return paginated_generator(self._comments_paginated)

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
    def author(self):
        data = self._get_prop("creator")
        return User(data["id"], self.client, data = data)

    @property
    def source(self):
        return self._get_prop("source")

    @property
    def is_original(self):
        return self.source is None

    @property
    def is_featured(self):
        return self._get_prop("is_featured")

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

class Comment(CommentMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._post == None and self._account_data_payload["cid"] == None:
            raise Exception("This needs a post")

        self._url = f"{self.client.api}/content/{self.cid}/comments" if not self._root else f"{self.client.api}/content/{self.cid}/comments/{self._root}/replies"

    def __repr__(self):
        return self.content

    def __eq__(self, other):
        return self.id == other

    def _replies_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/{self.id}/replies", "replies", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self.client, data = item, post = self.cid, root = self.id) for item in data["items"]]

        return format_paginated(data, items)

    # public methods

    def delete(self):
        response = requests.delete(f"{self._url}/{self.id}", headers = self.client.headers)

        return response

    # public generators

    @property
    def replies(self):
        return paginated_generator(self._replies_paginated)

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

class Channel:
    """
    Sendbird messagable channel.
    Docs in progress
    """
    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.url = data["channel_url"]
        self.id = data["channel_id"]
        self.type = data["channel_type"]

class MessageContext:
    """
    Sendbird message context
    Docs in progress
    """
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
