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
    def __init__(self, id, client, data = None, paginated_size = 30):
        super().__init__(id, client, data = data, paginated_size = paginated_size)

    @property
    def _account_data(self):
        if self._update or self._account_data_payload is None:
            self._update = False
            response = requests.get(self._url, headers = self.client.sendbird_headers)

            if response.status_code == 403:
                self._account_data_payload = {}
                return self._account_data_payload

            try:
                self._account_data_payload = response.json()
            except KeyError:
                raise Exception(response.text)

        return self._account_data_payload

class User(ObjectMixin):
    """
    Ifunny User object.
    Params taken from parent ObjectMixin
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chat_url = None
        self._url = f"{self.client.api}/users/{self.id}"

    def __repr__(self):
        return self.nick

    def __eq__(self, other):
        return self.id == other

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

        :param type: reason for report \n
            hate   -> hate speech \n
            nude   -> nudity \n
            spam   -> spam posting \n
            target -> targeted harrassment \n
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
    """
    Ifunny Post object.
    Params taken from parent ObjectMixin
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = f"{self.client.api}/content/{self.id}"

    def __eq__(self, other):
        return self.id == other

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
        """
        :returns: Generator iterating post smiles

        :rtype: Generator<User>
        """
        return paginated_generator(self._smiles_paginated)

    @property
    def comments(self):
        """
        :returns: Generator iterating post comments

        :rtype: Generator<Comment>
        """
        return paginated_generator(self._comments_paginated)

    # public properties

    # authentication independant attributes

    @property
    def smile_count(self):
        """
        :returns: post's smile count
        :rtype: int
        """
        return self._get_prop("num")["smiles"]

    @property
    def unsmile_count(self):
        """
        :returns: post's unsmile count
        :rtype: int
        """
        return self._get_prop("num")["unsmiles"]

    @property
    def guest_smile_count(self):
        """
        :returns: post's smile count by guests
        :rtype: int
        """
        return self._get_prop("num")["guest_smiles"]

    @property
    def comment_count(self):
        """
        :returns: post's comment count
        :rtype: int
        """
        return self._get_prop("num")["comments"]

    @property
    def views(self):
        """
        :returns: post's view count count
        :rtype: int
        """
        return self._get_prop("num")["views"]

    @property
    def republication_count(self):
        """
        :returns: post's republication count
        :rtype: int
        """
        return self._get_prop("num")["republished"]

    @property
    def shares(self):
        """
        :returns: post's share count
        :rtype: int
        """
        return self._get_prop("num")["shares"]

    @property
    def author(self):
        """
        :returns: post's author
        :rtype: User
        """
        data = self._get_prop("creator")
        return User(data["id"], self.client, data = data)

    @property
    def source(self):
        """
        :returns: post's instance on it's original account, if a republication
        :rtype: Post
        """
        return self._get_prop("source")

    @property
    def is_original(self):
        """
        :returns: True if this post is OC
        :rtype: bool
        """
        return self.source is None

    @property
    def is_featured(self):
        """
        :returns: True if this post is featured
        :rtype: bool
        """
        return self._get_prop("is_featured")

    @property
    def is_pinned(self):
        """
        :returns: True if this post is pinned on it's authors profile
        :rtype: bool
        """
        return self._get_prop("is_pinned")

    @property
    def is_abused(self):
        """
        :returns: True if this post was removed by moderators
        :rtype: bool
        """
        return self._get_prop("is_abused")

    @property
    def type(self):
        """
        :returns: content ype of a post
        :rtype: str
        """
        return self._get_prop("type")

    @property
    def tags(self):
        """
        :returns: the tags of a post
        :rtype: list<str>
        """
        return self._get_prop("tags")

    @property
    def visibility(self):
        """
        :returns: the visibility of a post
        :rtype: str (public, subscribers, ect)
        """
        return self._get_prop("visibility")

    @property
    def state(self):
        """
        :returns: the publicication state of the post
        :rtype: str (published, ect)
        """
        return self._get_prop("state")

    @property
    def boostable(self):
        """
        :returns: True if this post is able to be boosted
        :rtype: bool
        """
        return self._get_prop("can_be_boosted")

    @property
    def created_at(self):
        """
        :returns: creation date timestamp
        :rtype: int
        """
        return self._get_prop("date_created")

    @property
    def published_at(self):
        """
        :returns: creation date timestamp
        :rtype: int
        """
        return self._get_prop("published_at")

    @property
    def content_url(self):
        """
        :returns: url pointing to the full sized image
        :rtype: str
        """
        return self._get_prop("url")

    @property
    def content(self):
        """
        :returns: image or video data from the post
        :rtype: bytes
        """
        return requests.get(self.content_url).content

    # authentication dependant attributes

    @property
    def is_republished(self):
        """
        :returns: True if this pic is republished by the attached client
        :rtype: bool
        """
        return self._get_prop("is_republished")

    @property
    def smiled(self):
        """
        :returns: True if this pic is smiled by the attached client
        :rtype: bool
        """
        return self._get_prop("is_smiled")

    @property
    def unsmiled(self):
        """
        :returns: True if this pic is unsmiled by the attached client
        :rtype: bool
        """
        return self._get_prop("is_unsmiled")

class Comment(CommentMixin):
    """
    Ifunny Comment object.
    Params taken from parent class CommentMixin
    """
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
        """
        Delete a comment belonging to you or on your post.

        :returns: True if the post was deleted (if the POST response was 200), else False
        :rtype: bool
        """
        response = requests.delete(f"{self._url}/{self.id}", headers = self.client.headers)

        return response.status_code == 200

    # public generators

    @property
    def replies(self):
        """
        :returns: Generator iterating comment replies

        :rtype: Generator<Comment>
        """
        return paginated_generator(self._replies_paginated)

    # public properties

    # authentication independant properties

    @property
    def content(self):
        """
        :returns: the text content of a comment
        :rtype: str
        """
        value = self._get_prop("text")
        return value if value else ""

    @property
    def cid(self):
        """
        :returns: the cid of this comment. A comments CID is the id of the post it's attached to
        :rtype: str
        """
        if type(self._post) is str:
            self._post = Post(self._post, self.client)

        if self._post:
            return self._post.id

        if not self.__cid:
            self.__cid = self._get_prop("cid")

        return self.__cid

    @property
    def state(self):
        """
        :retunrs: the state of the comment. Top comments are state top, and all others are state normal
        :rtype: str (top, normal)
        """
        return self._get_prop("state")

    @property
    def author(self):
        """
        :returns: the comment author
        :rtype: Use
        """
        data = self._get_prop("user")
        return User(data["id"], self.client, data = data)

    @property
    def post(self):
        """
        :returns: the post that this comment is on
        :rtype: Post
        """
        return Post(self.cid, self.client)

    @property
    def root(self):
        """
        :returns: this comments root parent, or None if comment is root
        :rtype: Comment, or None
        """
        if self.is_root:
            return None

        return Comment(self._get_prop("root_comm_id"), self.client, post = self.cid)

    @property
    def smile_count(self):
        """
        :returns: number of smiles on this comment
        :rtype: int
        """
        return self._get_prop("num")["smiles"]

    @property
    def unsmile_count(self):
        """
        :returns: number of unsmiles on this comment
        :rtype: int
        """
        return self._get_prop("num")["unsmiles"]

    @property
    def reply_count(self):
        """
        :returns: number of replies on this comment
        :rtype: int
        """
        return self._get_prop("num")["replies"]

    @property
    def created_at(self):
        """
        :returns: creation date timestamp
        :rtype: int
        """
        self._get_prop("date")

    @property
    def depth(self):
        """
        :returns: the depth of this comment
        :rtype: int
        """
        if self.is_root:
            return 0

        return self._get_prop("depth")

    @property
    def is_root(self):
        """
        :returns: True if this comment has been edited
        :rtype: bool
        """
        return not self._get_prop("is_reply")

    @property
    def is_deleted(self):
        """
        :returns: True if this comment has been deleted
        :rtype: bool
        """
        value = self._get_prop("is_deleted")
        return value if value else False

    @property
    def is_edited(self):
        """
        :returns: True if this comment has been edited
        :rtype: bool
        """
        return self._get_prop("is_edited")

    @property
    def attached_post(self):
        """
        :returns: the attached post, if any
        :rtype: Post, or None
        """
        data = self._get_prop("attachments")["content"]

        if len(data) == 0:
            return None

        return Post(data[0]["id"], self.client, data = data[0])

    @property
    def mentioned_users(self):
        """
        :returns: a list of mentioned users, if any
        :rtype: list<User>
        """
        data = self._get_prop("attachments")["mention_user"]

        if len(data) == 0:
            return []

        return [User(item["user_id"], self.client) for item in data]

    # authentication dependant properties

    @property
    def is_smiled(self):
        """
        :returns: True if this comment is smile by the attached client
        :rtype: bool
        """
        return self._get_prop("is_smiled")

    @property
    def is_unsmiled(self):
        """
        :returns: True if this comment is unsmiled by the attached client
        :rtype: bool
        """
        return self._get_prop("is_unsmiled")

class Channel(SendbirdMixin):
    """
    Sendbird messagable channel.
    Docs in progress
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_url = self.id
        self._url = f"{self.client.sendbird_api}/group_channels/{self.id}/"

    def join(self):
        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}/members", headers = self.client.headers)
        print(self.client.headers)

        return True if response.status_code == 200 else False

    def send_message(self, message):
        message_data = {
            "channel_url"   : self.channel_url,
            "message"       : message
        }

        response = self.client.socket.send(f"MESG{json.dumps(message_data, separators = (',', ':'))}\n")

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

        return self.client.socket.send(f"FILE{json.dumps(response_data, separators = (',', ':'))}\n")

class Message:
    """
    Sendbird message object. Spawned when a message is recieved.

    :param data: message json, data after prefix in a sendbird websocket response
    :param client: client that the object belongs to

    :type data: dict
    :type client: Client
    """
    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.__message = None
        self.__channel_url = None
        self.__channel = None

    def __repr__(self):
        return self.content

    @property
    def channel(self):
        """
        :returns: Channel that this message exists in
        :rtype: Channel
        """
        if not self.__channel:
            self.__channel = Channel(self.channel_url, self.client)

        return self.__channel

    @property
    def content(self):
        """
        :returns: String content of the message
        :rtype: str
        """
        if not self.__message:
            self.__message = self.__data["message"]

        return self.__message

    @property
    def channel_url(self):
        """
        :returns: channel url for this messages channel
        :rtype: str
        """
        if not self.__channel_url:
            self.__channel_url = self.__data["channel_url"]

        return self.__channel_url

    @property
    def send(self):
        """
        :returns: the send() method of this messages channel for easy replies
        :rtype: function
        """
        return self.channel.send_message

    @property
    def send_file_url(self):
        """
        :retunrs: the send_file_url() method of this messages channel for easy replies
        :rtype: function
        """
        return self.channel.send_file_url

class Invite:
    """
    Message invitation class. Spawned when an imcomming Channel is recieved

    :param data: channel json, data after prefix in a sendbird websocket response
    :param client: client that the object belongs to

    :type data: dict
    :type client: Client
    """

    _status_codes = {
        10000: "accepted",
        10020: "new",
        10022: "rejected"
    }

    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.__channel = None
        self.__channel_url = None
        self.__inviter = None
        self.__invitees = None
        self.__url = None

    def accept(self):
        """
        Accept an incomming invitation, if it is from a user.
        If it is not, the method will return nothing.

        :returns: Channel that was joined, or None
        :rtype: Channel, or None
        """
        if not self.inviter:
            return None

        headers = self.client.sendbird_headers

        data = json.dumps({
            "user_id": self.client.id
        })

        response = requests.put(f"{self.url}/accept", headers = headers, data = data)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()
        return self.channel

    def decline(self):
        """
        Decline an incomming invitation, if it is from a user.
        If it is not, the method will return nothing.
        """
        if not self.inviter:
            return None

        headers = self.client.sendbird_headers

        data = json.dumps({
            "user_id": self.client.id
        })

        response = requests.put(f"{self.url}/decline", headers = headers, data = data)

    @property
    def url(self):
        """
        :retunrs: the request url to the incomming Channel
        :rtype: str
        """
        if not self.__url:
            self.__url = f"{self.client.sendbird_api}/group_channels/{self.channel_url}"

        return self.__url

    @property
    def channel_url(self):
        """
        :retunrs: the url to the incomming Channel
        :rtype: str
        """
        if not self.__channel_url:
            self.__channel_url = self.__data["channel_url"]

        return self.__channel_url

    @property
    def channel(self):
        """
        :retunrs: the incomming Channel
        :rtype: Channel
        """
        if not self.__channel:
            self.__channel = Channel(self.channel_url, self.client)

        return self.__channel

    @property
    def inviter(self):
        """
        :retunrs: the user who dispatched an invite to this group, or None
        :rtype: User, or None
        """
        if not self.__inviter:
            inviter = self.__data["data"]["inviter"]

            if not inviter:
                self.__inviter = None
                return self.__inviter

            self.__inviter = User(inviter["user_id"], self.client)

        return self.__inviter

    @property
    def invitees(self):
        """
        :returns: the users who were invited with this instance of an incomming Channel
        :rtype: list<User>, or None
        """
        if not self.__invitees:
            invitees = self.__data["data"]["invitees"]
            self.__invitees = [User(user["user_id"], self.client) for user in invitees]

        return self.__invitees

    @property
    def status(self):
        """
        :returns: the status of the incomming channel data
        :rtype: str
        """
        return self._status_codes.get(self.__data["cat"], f"unknown: {self.__data['cat']}")
