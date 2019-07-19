import requests, json

from urllib.parse import quote_plus as urlencode

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

            try:
                self._account_data_payload = response.json()["data"]
            except KeyError:
                raise BadAPIResponse(f"{response.url}, {response.text}")

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
    def by_nick(cls, nickname, client):
        """
        Get a user from their nickname.

        :param nickname: nickname of the user to query. If this user does not exist, nothing will be returned
        :param client: the Client to bind the returned user object to

        :type nickname: str
        :type client: Client

        :returns: A User with a given nickname, if they exist
        :rtype: User, or None
        """
        response = requests.get(f"{client.api}/users/by_nick/{nickname}", headers = client.headers)

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
        :retunrs: is this user verified?
        :rtype: bool
        """
        return self._get_prop("is_verified")

    @property
    def is_banned(self):
        """
        :retunrs: is this user banned?
        :rtype: bool
        """
        return self._get_prop("is_banned")

    @property
    def is_deleted(self):
        """
        :retunrs: is this user deleted?
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
        :retunrs: this users chat url, if ``user.can_chat``
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
    def chat_channel(self):
        """
        :retunrs: this users chat channel, if ``user.can_chat``
        :rtype: Channel
        """
        if self.chat_url:
            return Channel(self.chat_url, self.client)

        return None

    # authentication dependant attributes

    @property
    def blocked(self):
        """
        :retunrs: is this user blocked by me?
        :rtype: bool
        """
        return self._get_prop("is_blocked")

    @property
    def blocking_me(self):
        """
        :retunrs: is this user blocking me?
        :rtype: bool
        """
        return self._get_prop("are_you_blocked")

    @property
    def can_chat(self):
        """
        :retunrs: can I chat with this user?
        :rtype: bool
        """
        return self._get_prop("is_available_for_chat", False)

    @property
    def subscribed_to_updates(self):
        """
        :retunrs: is this user subscribed to updates?
        :rtype: bool
        """
        return self._get_prop("is_subscribed_to_updates", False)

    @property
    def is_subscribed(self):
        """
        :retunrs: is this user subscribed to me?
        :rtype: bool
        """
        return self._get_prop("is_in_subscribers", False)

    @property
    def is_subscription(self):
        """
        :retunrs: am I subscribed to this user?
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
        Un-republish this post. This should work on an instance of this post from any User. If this post is not republished, nothing will happen.

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
        Set the tags on your own post. If the post is not owned by the client, NotOwnContent exception is raised
        Tags cannot include space characters, so those will be replace dropped

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
        Delete a post owned by the Client

        :retunrs: self

        :rtype: Post
        """

        response = requests.delete(self._url, headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(self.text)

        return self.fresh

    def pin(self):
        """
        Pin a post to the client user

        :returns: self

        :rtype: Post
        """

        response = requests.put(f"{self._url}/pinned", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def unpin(self):
        """
        Unpin a post to the client user

        :returns: self

        :rtype: Post
        """

        response = requests.delete(f"{self._url}/pinned", headers = self.client.headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

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
    def is_pinned(self):
        """
        :returns: is this post pinned on it's authors profile?
        :rtype: bool
        """
        return self._get_prop("is_pinned")

    @property
    def is_abused(self):
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

    # authentication dependant attributes

    @property
    def is_republished(self):
        """
        :returns: is this post a republication?
        :rtype: bool
        """
        return self._get_prop("is_republished")

    @property
    def smiled(self):
        """
        :returns: did I smile this post?
        :rtype: bool
        """
        return self._get_prop("is_smiled")

    @property
    def unsmiled(self):
        """
        :returns: did I unsmile this post?
        :rtype: bool
        """
        return self._get_prop("is_unsmiled")

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

    def __eq__(self, other):
        return self.id == other

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
        value = self._get_prop("is_deleted")
        return value if value else False

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
