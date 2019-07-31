import requests, json

from urllib.parse import quote_plus as urlencode
from collections.abc import Iterable

from ifunny import objects

from ifunny.util.methods import invalid_type, paginated_format, paginated_data, paginated_generator, get_slice
from ifunny.util.exceptions import NoContent, TooManyMentions, BadAPIResponse, FailedToComment, NotOwnContent, OwnContent

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

            if response.status_code == 404:
                self._account_data_payload = {"is_deleted" : True}
                return self._account_data_payload

            try:
                self._account_data_payload = response.json()["data"]
            except KeyError:
                raise BadAPIResponse(f"{response.url}, {response.text}")

        return self._account_data_payload

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


    def __eq__(self, other):
        return self.id == other

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
    """
    iFunny User object.

    :param id: id of the user
    :param client: Client that the user belongs to
    :param data: A data payload for the user to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chat_url = None
        self._url = f"{self.client.api}/users/{self.id}"

    def __repr__(self):
        return self.nick

    # paginated data

    def _timeline_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size
        limit = min(100, limit)

        data = paginated_data(
            f"{self.client.api}/timelines/users/{self.id}", "content", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Post(item["id"], self.client, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _subscribers_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/subscribers", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _subscriptions_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/subscriptions", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return paginated_format(data, items)

    # actions

    @classmethod
    def by_nick(cls, nick, client):
        """
        Get a user from their nick.

        :param nick: nick of the user to query. If this user does not exist, nothing will be returned
        :param client: the Client to bind the returned user object to

        :type nick: str
        :type client: Client

        :returns: A User with a given nick, if they exist
        :rtype: User, or None
        """
        response = requests.get(f"{client.api}/users/by_nick/{nick}", headers = client.headers)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        response = response.json()
        return cls(response["data"]["id"], client, data = response["data"])

    def subscribe(self):
        """
        Subscribe to a user

        :returns: self
        :rtype: User
        """
        response = requests.put(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unsubscribe(self):
        """
        Unsubscribe from a user

        :returns: self
        :rtype: User
        """
        response = requests.delete(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return True

    def block(self, type = "user"):
        """
        Block a user, either by account or device.

        :param type: Type of block. user blocks a user, installation blocks all users tied to a device

        :type type: str

        :returns: self

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
                return self.fresh

            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unblock(self):
        """
        Unblock a user.

        :returns: self
        :rtype: User
        """
        params = {
            "type": "user"
        }

        response = requests.delete(f"{self.client.api}/users/my/blocked/{self.id}", params = params, headers = self.client.headers)

        if response.status_code != 200:
            if response.json().get("error") == "not_blocked":
                return False

            raise BadAPIResponse(f"{response.url}, {response.text}")

        return True

    def report(self, type):
        """
        Report a user.

        :param type: Reason for report \n
            hate   -> hate speech \n
            nude   -> nudity \n
            spam   -> spam posting \n
            target -> targeted harrassment \n
            harm   -> encouraging harm or violence

        :type type: str

        :returns: self

        :rtype: User
        """
        valid = ["hate", "nude", "spam", "target", "harm"]

        if type not in valid:
            raise TypeError(f"type must be one of {', '.join(valid)}, not {type}")

        params = {
            "type": type
        }

        response = requests.put(f"{self._url}/abuses", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def subscribe_to_updates(self):
        """
        Subscribe to update notifications from this User.

        :returns: self
        :rtype: User
        """
        response = requests.put(f"{self.client.api}/users/{self.id}/updates_subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unsubscribe_to_updates(self):
        """
        Unsubscribe to update notifications from this User.

        :returns: self
        :rtype: User
        """
        response = requests.delete(f"{self.client.api}/users/{self.id}/updates_subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def set_nick(self, value):
        """
        Change the nick of a User.
        This user must be you

        :param value: what to change the nick to

        :type value: str

        :returns: self
        :rtype: User
        """
        data = {
            "nick"                      : str(value),
            "messaging_privacy_status"  : self.chat_privacy,
            "is_private"                : 0
        }

        response = requests.put(f"{self.client.api}/account", data = data, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return response

    def set_about(self, value):
        """
        Change the about of a User.
        This user must be you

        :param value: what to change the about to

        :type value: str

        :returns: self
        :rtype: User
        """
        data = {
            "about"                     : str(value),
            "messaging_privacy_status"  : self.chat_privacy,
            "is_private"                : 0
        }

        response = requests.put(f"{self.client.api}/account", data = data, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return response

    # public generators

    @property
    def timeline(self):
        """
        :returns: generator iterating user posts

        :rtype: generator<Post>
        """
        return paginated_generator(self._timeline_paginated)

    @property
    def subscribers(self):
        """
        :returns: generator iterating user subscipbers

        :rtype: generator<User>
        """
        return paginated_generator(self._subscribers_paginated)

    @property
    def subscriptions(self):
        """
        :returns: generator iterating user subscriptions

        :rtype: generator<User>
        """
        return paginated_generator(self._subscriptions_paginated)

    # public properties

    # authentication independant attributes

    @property
    def nick(self):
        """
        :returns: this users nickname
        :rtype: str
        """
        return self._get_prop("nick")

    @nick.setter
    def nick(self, value):
        if self != self.client.user:
            raise Forbidden("You cannot change the nick of another user")

        self.set_nick(str(value))

    @property
    def about(self):
        """
        :returns: this users about section
        :rtype: str
        """
        return self._get_prop("about")

    @about.setter
    def about(self, value):
        if self != self.client.user:
            raise Forbidden("You cannot change the about of another user")

        self.set_about(str(value))

    @property
    def posts(self):
        """
        :returns: this users post count
        :rtype: int
        """
        if self._get_prop("num").get("featured"):
            return self._get_prop("num").get("featured")
        else:
            return self.fresh._get_prop("num").get("featured")

    @property
    def featured(self):
        """
        :returns: this users feature count
        :rtype: int
        """
        if self._get_prop("num").get("featured"):
            return self._get_prop("num").get("featured")
        else:
            return self.fresh._get_prop("num").get("featured")

    @property
    def total_smiles(self):
        """
        :returns: this users smile count
        :rtype: int
        """
        if self._get_prop("num").get("total_smiles"):
            return self._get_prop("num").get("total_smiles")
        else:
            return self.fresh._get_prop("num").get("total_smiles")

    @property
    def subscriber_count(self):
        """
        :returns: this users subscriber count
        :rtype: int
        """
        if self._get_prop("num").get("subscribers"):
            return self._get_prop("num").get("subscribers")
        else:
            return self.fresh._get_prop("num").get("subscribers")

    @property
    def subscription_count(self):
        """
        :returns: this users subscruption count
        :rtype: int
        """
        if self._get_prop("num").get("subscriptions"):
            return self._get_prop("num").get("subscriptions")
        else:
            return self.fresh._get_prop("num").get("subscriptions")

    @property
    def is_verified(self):
        """
        :returns: is this user verified?
        :rtype: bool
        """
        return self._get_prop("is_verified")

    @property
    def is_banned(self):
        """
        :returns: is this user banned?
        :rtype: bool
        """
        return self._get_prop("is_banned")

    @property
    def is_deleted(self):
        """
        :returns: is this user deleted?
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
        :returns: this users meme experience rank
        :rtype: str
        """
        return self._get_prop("meme_experience")["rank"]

    @property
    def nick_color(self):
        """
        :returns: this users nickname color
        :rtype: str
        """
        return self._get_prop("nick_color")

    @property
    def chat_privacy(self):
        """
        :returns: this users chat privacy settings (privacy, public, subscribers)
        :rtype: str
        """
        return self._get_prop("messaging_privacy_status")

    @property
    def chat_url(self):
        """
        :returns: this users chat url, if ``user.can_chat``
        :rtype: str
        """
        if not self.can_chat or self == self.client.user:
            return None

        if not self._chat_url:
            data = {
                "chat_type": "chat",
                "users": self.id
            }

            response = requests.post(f"{self.client.api}/chats", headers = self.client.headers, data = data)

            self._chat_url = response.json()["data"].get("chatUrl")

        return self._chat_url

    @property
    def chat(self):
        """
        :returns: this users chat chat, if ``user.can_chat``
        :rtype: Chat
        """
        if self.chat_url:
            return objects.Chat(self.chat_url, self.client)

        return None

    @property
    def pic_url(self):
        """
        :returns: url to this accounts profile image, if any
        :rtype: str, or None
        """
        _data = self._get_prop("photo")
        return _data.get("url") if _data else None

    # authentication dependant attributes

    @property
    def blocked(self):
        """
        :returns: is this user blocked by me?
        :rtype: bool
        """
        return self._get_prop("is_blocked")

    @blocked.setter
    def blocked(self, value):
        if value:
            self.block()
        else:
            self.unblock()

    @property
    def blocking_me(self):
        """
        :returns: is this user blocking me?
        :rtype: bool
        """
        return self._get_prop("are_you_blocked")

    @property
    def can_chat(self):
        """
        :returns: can I chat with this user?
        :rtype: bool
        """
        return self._get_prop("is_available_for_chat", False)

    @property
    def subscribed_to_updates(self):
        """
        :returns: is this user subscribed to updates?
        :rtype: bool
        """
        return self._get_prop("is_subscribed_to_updates", False)

    @property
    def is_subscribed(self):
        """
        :returns: is this user subscribed to me?
        :rtype: bool
        """
        return self._get_prop("is_in_subscribers", False)

    @property
    def is_subscription(self):
        """
        :returns: am I subscribed to this user?
        :rtype: bool
        """
        return self._get_prop("is_in_subscriptions", False)

class Post(ObjectMixin):
    """
    iFunny Post object

    :param id: id of the post
    :param client: Client that the post belongs to
    :param data: A data payload for the post to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = f"{self.client.api}/content/{self.id}"

    # paginated data

    def _smiles_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/smiles", "users", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def _comments_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/comments", "comments", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self.client, data = item, post = self) for item in data["items"]]

        return paginated_format(data, items)

    # public methods

    def add_comment(self, text = None, post = None, user_mentions = None):
        """
        Add a comment to a post.
        At least one of the parameters must be used, as users shoud not post empty comments.

        :param text: Text of the comment, if any
        :param post: Post to post in the comment, if any. Can be a post id or a Post object, but the Post in reference must belong to the client creating the comment
        :param user_mentions: Users to mention, if any. Mentioned users must have their nick in the comment, and will be mentioned at the first occurance of their nick

        :type text: str
        :type post: Post or str
        :type user_mentions: list<User>

        :returns: the posted comment
        :rtype: Comment
        """

        if not any((text, post, user_mentions)):
            raise NoContent("Must have at least one of (text, post, user_mentions)")

        data = {}

        if text:
            data["text"] = str(text)

        if user_mentions:
            if any([user.nick not in text for user in user_mentions]):
                raise TooManyMentions("Not all user mentions are included in the text")

            formatted = [":".join([user.id, get_slice(text, user.nick)]) for user in user_mentions]
            data["user_mentions"] = ";".join(formatted)

        if post:
            if isinstance(post, str):
                post = Post(post, self.client)

            if post.author != self.client.user:
                raise NotOwnContent("Users can only add ther own posts to a meme")

            data["content"] = post.id

        response = requests.post(f"{self._url}/comments", data = data, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        response = response.json()

        if response["data"]["id"] == "000000000000000000000000":
            raise FailedToComment(f"Failed to add the comment {text}. Are you posting the same comment too fast?")

        return Comment(response["data"]["id"], self.client, data = response["data"]["comment"])

    def smile(self):
        """
        smile a post. If already smiled, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.put(f"{self._url}/smiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def remove_smile(self):
        """
        Remove a smile from a post. If none exists, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.delete(f"{self._url}/smiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unsmile(self):
        """
        Unsmile a post. If already unsmiled, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.put(f"{self._url}/unsmiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def remove_unsmile(self):
        """
        Remove an unsmile from a post. If none exists, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.delete(f"{self._url}/unsmiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def republish(self):
        """
        Republish this post. If this post is already republished by the client, nothing will happen.

        :returns: republished instance of this post, or None if already republished
        :rtype: Post, or None
        """
        response = requests.post(f"{self._url}/republished", headers = self.client.headers)

        if response.status_code == 403:
            return None

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return Post(response.json()["data"]["id"], self.client)

    def remove_republish(self):
        """
        Un-republish this post. This should work on an instance of this post from any User.
        If this post is not republished, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.delete(f"{self._url}/republished", headers = self.client.headers)

        if response.status_code == 403:
            return self

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def report(self, type):
        """
        Report a post.

        :param type: Reason for report \n
            hate   -> hate speech \n
            nude   -> nudity \n
            spam   -> spam posting \n
            target -> targeted harrassment \n
            harm   -> encouraging harm or violence

        :type type: str

        :returns: self

        :rtype: Post
        """
        valid = ["hate", "nude", "spam", "target", "harm"]

        if self.author == self.client.user:
            raise OwnContent("Client can't report their own content")

        if type not in valid:
            raise TypeError(f"type must be one of {', '.join(valid)}, not {type}")

        params = {
            "type": type
        }

        response = requests.put(f"{self._url}/abuses", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def set_tags(self, tags):
        """
        Set the tags on your own post. If the post is not owned by the client, NotOwnContent exception is raised.
        Tags cannot include space characters, so those will be replace dropped.

        :param tags: list of tags to add to set

        :type tags: list<str>

        :returns: self

        :rtype: Post

        :raises: NotOwnContent
        """

        if self.author != self.client.user:
            raise NotOwnContent(f"Post must belong to the client, but belongs to {self.author.nick}")

        tags = ",".join([f"\"{tag.replace(' ', '')}\"" for tag in tags])

        data = f"tags=[{tags}]"

        response = requests.put(f"{self._url}/tags", headers = self.client.headers, data = data)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def delete(self):
        """
        Delete a post owned by the Client.

        :returns: self

        :rtype: Post
        """

        response = requests.delete(self._url, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def pin(self):
        """
        Pin a post to the client user.
        Note that trying to pin a pinned post will return a ``403``.

        :returns: self

        :rtype: Post
        """

        response = requests.put(f"{self._url}/pinned", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unpin(self):
        """
        Unpin a post to the client user.

        :returns: self

        :rtype: Post
        """

        response = requests.delete(f"{self._url}/pinned", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def set_schedule(self, schedule):
        """
        Update a delated posts scheduled time
        If post is not delated, nothing will happen

        :param schedule: new timestamp to be posted at

        :type schedule: int

        :returns: self
        :rtype: Post
        """
        if not self.state == "delayed":
            return None

        data = {
            "publish_at"    : int(schedule),
            "visibility"    : self.visibility,
            "tags"          : json.dumps(self.tags)
        }

        response = requests.patch(f"{self._url}", data = data, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self

    def set_visibility(self, visibility):
        """
        Update a delated posts visibility
        If post is not delated, nothing will happen

        :param visibility: visibility type. Can be of (``public``, ``subscribers``)

        :type visibility: str

        :returns: self
        :rtype: Post
        """
        if not self.state == "delated":
            return None

        if visibility not in {"public", "subscribers"}:
            raise ValueError(f"visibility cannot be {visibility}")

        data = {
            "visibility"    : visibility,
            "tags"          : json.dumps(self.tags)
        }

        response = requests.patch(f"{self._url}", data = data, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self

    # public generators

    @property
    def smiles(self):
        """
        :returns: generator iterating post smiles

        :rtype: generator<User>
        """
        return paginated_generator(self._smiles_paginated)

    @property
    def comments(self):
        """
        :returns: generator iterating post comments

        :rtype: generator<Comment>
        """
        return paginated_generator(self._comments_paginated)

    # private properties

    @property
    def _meta(self):
        return self._get_prop(self.type, {})

    # public properties

    # authentication independant attributes

    @property
    def smile_count(self):
        """
        :returns: post's smile count
        :rtype: int
        """
        if self._get_prop("num").get("smiles"):
            return self._get_prop("num").get("smiles")
        else:
            return self.fresh._get_prop("num").get("smiles")

    @property
    def unsmile_count(self):
        """
        :returns: post's unsmile count
        :rtype: int
        """
        if self._get_prop("num").get("unsmiles"):
            return self._get_prop("num").get("unsmiles")
        else:
            return self.fresh._get_prop("num").get("unsmiles")

    @property
    def guest_smile_count(self):
        """
        :returns: post's smile count by guests
        :rtype: int
        """
        if self._get_prop("num").get("guest_smiles"):
            return self._get_prop("num").get("guest_smiles")
        else:
            return self.fresh._get_prop("num").get("guest_smiles")

    @property
    def comment_count(self):
        """
        :returns: post's comment count
        :rtype: int
        """
        if self._get_prop("num").get("comments"):
            return self._get_prop("num").get("comments")
        else:
            return self.fresh._get_prop("num").get("comments")

    @property
    def views(self):
        """
        :returns: post's view count count
        :rtype: int
        """
        if self._get_prop("num").get("views"):
            return self._get_prop("num").get("views")
        else:
            return self.fresh._get_prop("num").get("views")

    @property
    def republication_count(self):
        """
        :returns: post's republication count
        :rtype: int
        """
        if self._get_prop("num").get("republished"):
            return self._get_prop("num").get("republished")
        else:
            return self.fresh._get_prop("num").get("republished")

    @property
    def shares(self):
        """
        :returns: post's share count
        :rtype: int
        """
        if self._get_prop("num").get("shares"):
            return self._get_prop("num").get("shares")
        else:
            return self.fresh._get_prop("num").get("shares")

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
        :returns: it this post original?
        :rtype: bool
        """
        return self.source is None

    @property
    def is_featured(self):
        """
        :returns: has this post been featured?
        :rtype: bool
        """
        return self._get_prop("is_featured")

    @property
    def pinned(self):
        """
        :returns: is this post pinned on it's authors profile?
        :rtype: bool
        """
        return self._get_prop("is_pinned")

    @pinned.setter
    def pinned(self, value):
        if value:
            self.pin()
        else:
            self.unpin()

    @property
    def abused(self):
        """
        :returns: was this post removed by moderators?
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

    @tags.setter
    def tags(self, value):
        if isinstance(value, str):
            value = [value]

        if not isinstance(value, Iterable):
            raise ValueError("value must be iterable")

        self.set_tags(list(value))

    @property
    def visibility(self):
        """
        :returns: the visibility of a post
        :rtype: str (public, subscribers, ect)
        """
        return self._get_prop("visibility")

    @visibility.setter
    def visibility(self, value):
        self.set_visibility(value)

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
        :returns: can this post be boosted?
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

    @property
    def caption(self):
        """
        :returns: caption text for ``caption`` type posts
        :rtype: str, or None
        """
        return self._meta.get("caption_text")

    # authentication dependant attributes

    @property
    def republished(self):
        """
        :returns: is this post a republication?
        :rtype: bool
        """
        return self._get_prop("is_republished")

    @republished.setter
    def republished(self, value):
        if value:
            self.republish()
        else:
            self.remove_republish()

    @property
    def smiled(self):
        """
        :returns: did I smile this post?
        :rtype: bool
        """
        return self._get_prop("is_smiled")

    @smiled.setter
    def smiled(self, value):
        if value:
            self.smile()
        else:
            self.remove_smile()

    @property
    def unsmiled(self):
        """
        :returns: did I unsmile this post?
        :rtype: bool
        """
        return self._get_prop("is_unsmiled")

    @unsmiled.setter
    def unsmiled(self, value):
        if value:
            self.unsmile()
        else:
            self.remove_unsmile()

class Comment(CommentMixin):
    """
    iFunny Comment object

    :param id: id of the comment
    :param client: Client that the comment belongs to
    :param data: A data payload for the comment to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__cid = None

        if self._post == None and self._account_data_payload["cid"] == None:
            raise BadAPIResponse("This needs a post")

        self._absolute_url = f"{self.client.api}/content/{self.cid}/comments"

        self._url = self._absolute_url if not self._root else f"{self.client.api}/content/{self.cid}/comments/{self._root}/replies"

    def __repr__(self):
        return self.content

    def _replies_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = paginated_data(
            f"{self._url}/{self.id}/replies", "replies", self.client.headers,
            limit = limit, prev = prev, next = next
        )

        items = [Comment(item["id"], self.client, data = item, post = self.cid, root = self.id) for item in data["items"]]

        return paginated_format(data, items)

    # public methods

    def reply(self, text = None, post = None, user_mentions = None):
        """
        Reply to a comment.
        At least one of the parameters must be used, as users shoud not post empty replys.

        :param text: Text of the reply, if any
        :param post: Post to post in the reply, if any. Can be a post id or a Post object, but the Post in reference must belong to the client creating the reply
        :param user_mentions: Users to mention, if any. Mentioned users must have their nick in the reply, and will be mentioned at the first occurance of their nick

        :type text: str
        :type post: Post or str
        :type user_mentions: list<User>

        :returns: the posted reply
        :rtype: Comment
        """

        if not any((text, post, user_mentions)):
            raise NoContent("Must have at least one of (text, post, user_mentions)")

        data = {}

        if text:
            data["text"] = str(text)

        if user_mentions:
            if any([user.nick not in text for user in user_mentions]):
                raise TooManyMentions("Not all user mentions are included in the text")

            formatted = [":".join([user.id, get_slice(text, user.nick)]) for user in user_mentions]
            data["user_mentions"] = ";".join(formatted)

        if post:
            if isinstance(post, str):
                post = Post(post, self.client)

            if post.author != self.client.user:
                raise NotOwnContent("Users can only add ther own posts to a meme")

            data["content"] = post.id

        response = requests.post(f"{self._url}/{self.id}/replies", data = data, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        response = response.json()

        if response["data"]["id"] == "000000000000000000000000":
            raise FailedToComment(f"Failed to add the comment {text}. Are you posting the same comment too fast?")

        return Comment(response["data"]["id"], self.client, data = response["data"]["comment"])

    def delete(self):
        """
        Delete a comment

        :returns: self

        :rtype: Comment
        """

        response = requests.delete(f"{self._absolute_url}/{self.id}", headers = self.client.headers)

        return self

    def smile(self):
        """
        smile a comment. If already smiled, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        response = requests.put(f"{self._absolute_url}/{self.id}/smiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def remove_smile(self):
        """
        Remove a smile from a comment. If none exists, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        response = requests.delete(f"{self._absolute_url}/{self.id}/smiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unsmile(self):
        """
        Unsmile a comment. If already unsmiled, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        response = requests.put(f"{self._absolute_url}/{self.id}/unsmiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def remove_unsmile(self):
        """
        Remove an unsmile from a comment. If none exists, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        response = requests.delete(f"{self._absolute_url}/{self.id}/unsmiles", headers = self.client.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def report(self, type):
        """
        Report a comment.

        :param type: Reason for report \n
            hate   -> hate speech \n
            nude   -> nudity \n
            spam   -> spam posting \n
            target -> targeted harrassment \n
            harm   -> encouraging harm or violence

        :type type: str

        :returns: self

        :rtype: User
        """
        valid = ["hate", "nude", "spam", "target", "harm"]

        if type not in valid:
            raise TypeError(f"type must be one of {', '.join(valid)}, not {type}")

        params = {
            "type": type
        }

        response = requests.put(f"{self._absolute_url}/{self.id}/abuses", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    # public generators

    @property
    def replies(self):
        """
        :returns: generator iterating comment replies
        :rtype: generator<Comment>
        """
        if not self.depth:
            for x in paginated_generator(self._replies_paginated):
                yield x
        else:
            for _comment in self.root.replies:
                if _comment.depth > self.depth and _comment._get_prop("parent_comm_id") == self.id:
                    yield _comment

    @property
    def children(self):
        """
        :returns: generator iterating direct children of comments
        :rtype: generator<Comment>
        """
        for x in self.replies:
            if x.depth == self.depth + 1:
                yield x

    @property
    def siblings(self):
        """
        :returns: generator iterating comment siblings
        :rtype: generator<Comment>
        """
        if self.is_root:
            return self.post.comments

        return self.parent.children

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
        :returns: the state of the comment. Top comments are state top, and all others are state normal
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
    def parent(self):
        """
        :returns: direct parent of this comment, or none for root comments
        :rtype: Comment
        """
        if self.is_root:
            return None

        return Comment(self._get_prop("parent_comm_id"), self.client, post = self.cid, root = self._get_prop("root_comm_id") if self.depth - 1 else None)

    @property
    def root(self):
        """
        :returns: this comments root parent, or self if comment is root
        :rtype: Comment
        """
        if self.is_root:
            return self

        return Comment(self._get_prop("root_comm_id"), self.client, post = self.cid)

    @property
    def smile_count(self):
        """
        :returns: number of smiles on this comment
        :rtype: int
        """
        if self._get_prop("num").get("smiles"):
            return self._get_prop("num").get("smiles")
        else:
            return self.fresh._get_prop("num").get("smiles")

    @property
    def unsmile_count(self):
        """
        :returns: number of unsmiles on this comment
        :rtype: int
        """
        if self._get_prop("num").get("unsmiles"):
            return self._get_prop("num").get("unsmiles")
        else:
            return self.fresh._get_prop("num").get("unsmiles")

    @property
    def reply_count(self):
        """
        :returns: number of replies on this comment
        :rtype: int
        """
        if self._get_prop("num").get("replies"):
            return self._get_prop("num").get("replies")
        else:
            return self.fresh._get_prop("num").get("replies")

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
        :returns: is this comment a top level (root) comment?
        :rtype: bool
        """
        return not self._get_prop("is_reply")

    @property
    def is_deleted(self):
        """
        :returns: has this comment been deleted?
        :rtype: bool
        """
        return self._get_prop("is_deleted", default = False)

    @property
    def is_edited(self):
        """
        :returns: has this comment been deleted?
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
        :returns: did I smile this comment?
        :rtype: bool
        """
        return self._get_prop("is_smiled")

    @property
    def is_unsmiled(self):
        """
        :returns: did I unsmile this comment?
        :rtype: bool
        """
        return self._get_prop("is_unsmiled")

class Notification:
    """
    General purpose notification object.
    Used to represent any notification recieved by a client

    :param data: iFunny api response that makes up the data
    :param client: iFunny client that the notification belongs to

    :type data: dict
    :type client: Client
    """
    def __init__(self, data, client):
        self.client = client
        self.type = data["type"]

        self.__data = data

    @property
    def user(self):
        """
        :returns: the user attatched to a notification, usually the one who triggered it.
        :rtype: User, or None
        """
        data = self.__data.get("user")

        if not data:
            return None

        return User(data["id"], self.client, data = data)

    @property
    def post(self):
        """
        :returns: the post attatched to a notification.
        :rtype: Post, or None
        """
        data = self.__data.get("content")

        if not data:
            return None

        return Post(data["id"], self.client, data = data)

    @property
    def comment(self):
        """
        :returns: the comment (root comment or reply) attatched to a notification
        :rtype: Comment, or None
        """
        if self.type == "reply_for_comment":
            data = self.__data.get("reply")
        else:
            data = self.__data.get("comment")

        if not data:
            return None

        post = self.__data["content"]["id"]

        if self.type == "reply_for_comment":
            root = self.__data["comment"]["id"]
            return Comment(data["id"], self.client, data = data, post = post, root = root)

        return Comment(data["id"], self.client, data = data, post = post)

    @property
    def created_at(self):
        """
        :returns: time at which the notification was created
        :rtype: time in seconds
        """
        return self.__data.get("date")

    @property
    def smile_count(self):
        """
        :returns: smile count, if self.type is "smile_tracker"
        :rtype: int, or None
        """
        return self.__data.get("smiles")

class Channel:
    def __init__(self, id, client, data = {}):
        """
        Object for ifunny explore channels.

        :param id: id of the feed
        :param client: Client that is requesting the feed

        :type id: str
        :type client: Client
        """
        self.client = client
        self.id = id
        self._feed_url = f"{self.client.api}/channels/{self.id}/items"
        self.__data = {}

    def _get_prop(self, key, default = None):
        return self.__data.get(key, default)

    def _feed_paginated(self, limit = 30, next = None, prev = None):
        data = paginated_data(
            self._feed_url, "content", self.client.headers,
            limit = limit, prev = prev, next = prev
        )

        items = [Post(item["id"], self.client, data = item) for item in data["items"]]

        return paginated_format(data, items)

    def __eq__(self, other):
        return self.id == other

    @property
    def feed(self):
        """
        generator for a channels feed.
        Each iteration will return the next channel post, in decending order of date posted

        :returns: generator iterating the channel feed
        :rtype: generator<Post>
        """
        return paginated_generator(self._feed_paginated)

class Digest(ObjectMixin):
    """
    iFunny digest object.
    represnets digests featured in explore, containing comments and posts

    :param id: id of the digest
    :param client: Client that the digest belongs to
    :param data: A data payload for the digest to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = f"{self.client.api}/digests/{self.id}"
        self._comments = False
        self._contents = False

    @property
    def _account_data(self):
        if self._update or self._account_data_payload is None:
            self._update = False

            params = {
                "contents"  : int(self._contents),
                "comments"  : int(self._comments)
            }

            response = requests.get(self._url, headers = self.client.headers, params = params)

            if response.status_code == 403:
                self._account_data_payload = {}
                return self._account_data_payload

            try:
                self._account_data_payload = response.json()["data"]
            except KeyError:
                raise BadAPIResponse(f"{response.url}, {response.text}")

        return self._account_data_payload

    def __repr__(self):
        return self.title

    def __len__(self):
        return self.post_count

    # public methods

    def read(self, count = None):
        """
        Mark posts in this digest as read.
        Will mark all unread by default

        :param count: number of posts to mark as read

        :type count: int

        :returns: self
        :rtype: Digest
        """
        count = count if count else self.unread_count
        response = requests.post(f"{self._url}/reads/{count}", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    # public properties

    @property
    def feed(self):
        """
        :returns: generator for posts that are in this digest
        :rtype: generator<Post>
        """
        self._contents = True

        for data in self._get_prop("items"):
            yield Post(data["id"], self.client, data = data)

    @property
    def comments(self):
        """
        :returns: subscriber comments that are in this digest
        :rtype: generator<Comment>
        """
        self._comments = True

        for data in self._get_prop("subscription_comments"):
            post = Post(data["contentId"], self.client)
            root = Comment(data["rootCommentId"], self.client, post = post) if data.get("rootCommentId") else None
            yield Comment(data["commentId"], self.client, post = post)

    @property
    def title(self):
        """
        :returns: the title of this digest
        :rtype: str
        """
        return self._get_prop("title")

    @property
    def smile_count(self):
        """
        :returns: number of smiles in this digest
        :rtype: int
        """
        return self._get_prop("likes")

    @property
    def total_smiles(self):
        """
        :returns: alias for ``Digest.smile_count```
        :rtype: int
        """
        return self.smile_count

    @property
    def comment_count(self):
        """
        :returns: number of comments in this digest
        :rtype: int
        """
        return self._get_prop("comments")

    @property
    def post_count(self):
        """
        :returns: number of posts in this digest
        :rtype: int
        """
        return self._get_prop("item_count")

    @property
    def unread_count(self):
        """
        :returns: number of unread posts in this digest
        :rtype: int
        """
        return self._get_prop("unreads")

    @property
    def count(self):
        """
        :returns: index of this digest
        :rtype: int
        """
        return self._get_prop("count")
