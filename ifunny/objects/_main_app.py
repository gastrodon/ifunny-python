import requests, json

from collections.abc import Iterable

from ifunny import objects
from ifunny.util import methods, exceptions
from ifunny.objects import _mixin as mixin


class User(mixin.ObjectMixin):
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
        self.__cover = None
        self.__image = None

    def __repr__(self):
        return self.nick

    # paginated data

    def _timeline_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size
        limit = min(100, limit)

        data = methods.paginated_data(
            f"{self.client.api}/timelines/users/{self.id}",
            "content",
            self.headers,
            limit = limit,
            prev = prev,
            next = next)

        items = [
            Post(item["id"], client = self.client, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _subscribers_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self._url}/subscribers",
                                      "users",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            User(item["id"], client = self.client, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _subscriptions_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self._url}/subscriptions",
                                      "users",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            User(item["id"], client = self.client, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _bans_paginated(self):
        data = methods.paginated_data(f"{self._url}/bans",
                                      "bans",
                                      self.headers,
                                      limit = None,
                                      prev = None,
                                      next = None)

        items = [
            objects.Ban(item["id"],
                        client = self.client,
                        user = self,
                        data = item) for item in data
        ]

        return items  # test login

    # actions

    @classmethod
    def by_nick(cls, nick, client = mixin.ClientBase()):
        """
        Get a user from their nick.

        :param nick: nick of the user to query. If this user does not exist, nothing will be returned
        :param client: the Client to bind the returned user object to

        :type nick: str
        :type client: Client

        :returns: A User with a given nick, if they exist
        :rtype: User, or None
        """
        errors = {404: {"raisable": exceptions.NotFound}}

        try:
            data = methods.request("get",
                                   f"{client.api}/users/by_nick/{nick}",
                                   headers = client.headers,
                                   errors = errors)["data"]

            return cls(data["id"], client = client, data = data)

        except exceptions.NotFound:
            return None

    def subscribe(self):
        """
        Subscribe to a user

        :returns: self
        :rtype: User
        """
        methods.request("put",
                        f"{self._url}/subscribers",
                        headers = self.headers)

        return self.fresh

    def unsubscribe(self):
        """
        Unsubscribe from a user

        :returns: self
        :rtype: User
        """
        methods.request("delete",
                        f"{self._url}/subscribers",
                        headers = self.headers)

        return self.fresh

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
            raise ValueError(f"type cannot be {type}")

        params = {"type": type}

        errors = {403: {"raisable": exceptions.Forbidden}}

        try:
            methods.request("put",
                            f"{self.client.api}/users/my/blocked/{self.id}",
                            params = params,
                            headers = self.headers,
                            errors = errors)

        except exceptions.Forbidden:
            pass

        return self.fresh

    def unblock(self):
        """
        Unblock a user.

        :returns: self
        :rtype: User
        """
        params = {"type": "user"}

        errors = {403: {"raisable": exceptions.Forbidden}}

        try:
            methods.request("delete",
                            f"{self.client.api}/users/my/blocked/{self.id}",
                            params = params,
                            headers = self.headers,
                            errors = errors)

        except exceptions.Forbidden:
            pass

        return self.fresh

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
            raise TypeError(
                f"type must be one of {', '.join(valid)}, not {type}")

        params = {"type": type}

        methods.request("put",
                        f"{self._url}/abuses",
                        headers = self.headers,
                        params = params)

        return self.fresh

    def subscribe_to_updates(self):
        """
        Subscribe to update notifications from this User.

        :returns: self
        :rtype: User
        """

        methods.request("put",
                        f"{self._url}/updates_subscribers",
                        headers = self.headers)

        return self.fresh

    def unsubscribe_to_updates(self):
        """
        Unsubscribe to update notifications from this User.

        :returns: self
        :rtype: User
        """
        methods.request("delete",
                        f"{self._url}/updates_subscribers",
                        headers = self.headers)

        return self.fresh

    def set_nick(self, value):
        """
        Change the nick of this User.
        This user must be you

        :param value: what to change the nick to

        :type value: str

        :returns: self
        :rtype: User
        """
        if not len(str(value)):
            raise ValueError("Nickname cannot be empty")

        data = {"nick": str(value)}

        if not self.client.nick_is_available(value):
            raise exceptions.Unavailable(f"Nick {value} is taken")

        response = requests.put(f"{self.client.api}/account",
                                data = data,
                                headers = self.headers)

        if response.status_code != 200:
            error = response.json()["error"]
            if error == "nickname_exists":
                raise exceptions.Unavailable(
                    f"nickname {value} is already taken")

            if error == "invalid_nickname":
                raise ValueError(f"nickname {value} is invalid")

            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def set_private(self, value):
        """
        Change the privacy value of this User
        This user must be you

        :param value: set this user to private?

        :type value: bool

        :returns: self
        :rtype: User
        """
        data = {
            "nick": self.nick,
            "messaging_privacy_status": self.chat_privacy,
            "is_private": int(bool(value))
        }

        response = requests.put(f"{self.client.api}/account",
                                data = data,
                                headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    def set_about(self, value):
        """
        Change the about of this User.
        This user must be you

        :param value: what to change the about to

        :type value: str

        :returns: self
        :rtype: User
        """
        data = {
            "about": str(value),
            "messaging_privacy_status": self.chat_privacy,
            "is_private": int(self.is_private)
        }

        response = requests.put(f"{self.client.api}/account",
                                data = data,
                                headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    # public generators

    @property
    def timeline(self):
        """
        :returns: generator iterating user posts

        :rtype: generator<Post>
        """
        return methods.paginated_generator(self._timeline_paginated)

    @property
    def subscribers(self):
        """
        :returns: generator iterating user subscipbers

        :rtype: generator<User>
        """
        return methods.paginated_generator(self._subscribers_paginated)

    @property
    def subscriptions(self):
        """
        :returns: generator iterating user subscriptions

        :rtype: generator<User>
        """
        return methods.paginated_generator(self._subscriptions_paginated)

    # public properties

    # authentication independant properties

    @property
    def nick(self):
        """
        :returns: this users nickname
        :rtype: str
        """
        return self.get("nick")

    @property
    def original_nick(self):
        """
        :returns: this users original nickname, if available
        :rtype: string
        """
        return self.get("original_nick")

    @property
    def about(self):
        """
        :returns: this users about section
        :rtype: str
        """
        return self.get("about")

    @property
    def post_count(self):
        """
        :returns: this users post count
        :rtype: int
        """
        try:
            return self.get("num")["total_posts"]
        except KeyError:
            return self.fresh.get("num").get("total_posts")

    @property
    def feature_count(self):
        """
        :returns: this users feature count
        :rtype: int
        """
        try:
            return self.get("num")["featured"]
        except KeyError:
            return self.fresh.get("num").get("featured")

    @property
    def smiles_count(self):
        """
        :returns: this users smile count
        :rtype: int
        """
        try:
            return self.get("num")["total_smiles"]
        except KeyError:
            return self.fresh.get("num").get("total_smiles")

    @property
    def subscriber_count(self):
        """
        :returns: this users subscriber count
        :rtype: int
        """
        return self.get("num")["subscribers"]

    @property
    def subscription_count(self):
        """
        :returns: this users subscruption count
        :rtype: int
        """
        return self.get("num")["subscriptions"]

    @property
    def is_verified(self):
        """
        :returns: is this user verified?
        :rtype: bool
        """
        return self.get("is_verified")

    @property
    def is_banned(self):
        """
        :returns: is this user banned?
        :rtype: bool
        """
        return self.get("is_banned")

    @property
    def is_deleted(self):
        """
        :returns: is this user deleted?
        :rtype: bool
        """
        return self.get("is_deleted")

    @property
    def days(self):
        """
        :returns: this users active days count
        :rtype: int
        """
        return self.get("meme_experience")["days"]

    @property
    def rank(self):
        """
        :returns: this users meme experience rank
        :rtype: str
        """
        return self.get("meme_experience")["rank"]

    @property
    def nick_color(self):
        """
        :returns: this users nickname color
        :rtype: str
        """
        return self.get("nick_color", "FFFFFF")

    @property
    def chat_privacy(self):
        """
        :returns: this users chat privacy settings (privacy, public, subscribers)
        :rtype: str
        """
        return self.get("messaging_privacy_status")

    @property
    def profile_image(self):
        """
        :returns: this accounts profile image, if any
        :rtype: Image, or None
        """
        if any({not self.__image, self._update}):
            _data = self.get("photo")
            self.__image = objects.Image(
                _data.get("url"), _data.get("bg_color")) if _data else None

        return self.__image

    @property
    def cover_image(self):
        """
        :returns: this accounts cover image, if any
        :rtype: Image, or None
        """

        if any({not self.__cover, self._update}):
            _data = self.get("cover_url")
            self.__cover = objects.Image(
                _data, self.get("cover_bg_color")) if _data else None

        return self.__cover

    @property
    def is_private(self):
        """
        :returns: is this profile private?
        :rtype: bool
        """
        return self.get("is_private")

    @property
    def rating(self):
        """
        :returns: rating of this user with level data
        :rtype: Rating
        """
        return objects.Rating(self,
                              client = self.client,
                              data = self.get("rating"))

    # authentication dependant properties

    @is_private.setter
    def is_private(self, value):
        if self != self.client.user:
            raise Forbidden("You cannot change the privacy of another user")

        self.set_private(bool(value))

    @nick.setter
    def nick(self, value):
        if self != self.client.user:
            raise Forbidden("You cannot change the nick of another user")

        self.set_nick(str(value))

    @about.setter
    def about(self, value):
        if self != self.client.user:
            raise Forbidden("You cannot change the about of another user")

        self.set_about(str(value))

    @property
    def bans(self):
        """
        :returns: this users bans
        :rtype: generator<Ban>
        """
        return (ban for ban in self._bans_paginated())  # test somehow?

    @property
    def chat_url(self):
        """
        :returns: this users chat url, if ``user.can_chat``
        :rtype: str
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        if not self.can_chat or self == self.client.user:
            return None

        if not self._chat_url:
            data = {"chat_type": "chat", "users": self.id}

            response = requests.post(f"{self.client.api}/chats",
                                     headers = self.headers,
                                     data = data)

            self._chat_url = response.json()["data"].get("chatUrl")

        return self._chat_url

    @property
    def chat(self):
        """
        :returns: this users chat, if ``user.can_chat``
        :rtype: Chat
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        if self.chat_url:
            return objects.Chat(self.chat_url, self.client)

        return None

    @property
    def is_blocked(self):
        """
        :returns: is this user blocked by me?
        :rtype: bool
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        return self.get("is_blocked")

    @is_blocked.setter
    def is_blocked(self, value):

        if value:
            self.block()
        else:
            self.unblock()

    @property
    def is_blocking_me(self):
        """
        :returns: is this user blocking me?
        :rtype: bool
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        return self.get("are_you_blocked")

    @property
    def can_chat(self):
        """
        :returns: can I chat with this user?
        :rtype: bool
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        return self.get("is_available_for_chat", False)

    @property
    def is_updates_subscription(self):
        """
        :returns: am I subscribed to updates from this user?
        :rtype: bool
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        return self.get("is_subscribed_to_updates", False)

    @is_updates_subscription.setter
    def is_updates_subscription(self, value):
        if value:
            self.subscribe_to_updates()
        else:
            self.unsubscribe_to_updates()

    @property
    def is_subscribed(self):
        """
        :returns: is this user subscribed to me?
        :rtype: bool
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        return self.get("is_in_subscribers", False)

    @property
    def is_subscription(self):
        """
        :returns: am I subscribed to this user?
        :rtype: bool
        """
        if not self.client.authenticated:
            raise exceptions.Forbidden("Not available for guests")
        return self.get("is_in_subscriptions", False)

    @is_subscription.setter
    def is_subscription(self, value):
        if value:
            self.subscribe()
        else:
            self.unsubscribe()


class Post(mixin.ObjectMixin):
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

    def __repr__(self):
        return self.link

    # paginated data

    def _smiles_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self._url}/smiles",
                                      "users",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            User(item["id"], client = self.client, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    def _comments_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self._url}/comments",
                                      "comments",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            Comment(item["id"], client = self.client, data = item, post = self)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

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
            raise exceptions.NoContent(
                "Must have at least one of (text, post, user_mentions)")

        data = {}

        if text:
            data["text"] = str(text)

        if user_mentions:
            if any([user.nick not in text for user in user_mentions]):
                raise exceptions.TooManyMentions(
                    "Not all user mentions are included in the text")

            formatted = [
                ":".join([user.id, methods.get_slice(text, user.nick)])
                for user in user_mentions
            ]
            data["user_mentions"] = ";".join(formatted)

        if post:
            if isinstance(post, str):
                post = Post(post, client = self.client)

            if post.author != self.client.user:
                raise exceptions.NotOwnContent(
                    "Users can only add ther own posts to a meme")

            data["content"] = post.id

        response = requests.post(f"{self._url}/comments",
                                 data = data,
                                 headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        response = response.json()

        if response["data"]["id"] == "000000000000000000000000":
            raise exceptions.RateLimit(
                f"Failed to add the comment {text}. Are you posting the same comment too fast?"
            )

        return Comment(response["data"]["id"],
                       client = self.client,
                       data = response["data"]["comment"])  # test log in

    def smile(self):
        """
        smile a post. If already smiled, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.put(f"{self._url}/smiles", headers = self.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def remove_smile(self):
        """
        Remove a smile from a post. If none exists, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.delete(f"{self._url}/smiles",
                                   headers = self.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def unsmile(self):
        """
        Unsmile a post. If already unsmiled, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.put(f"{self._url}/unsmiles",
                                headers = self.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def remove_unsmile(self):
        """
        Remove an unsmile from a post. If none exists, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.delete(f"{self._url}/unsmiles",
                                   headers = self.headers)

        if response.status_code != 200 and response.status_code != 403:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def republish(self):
        """
        Republish this post. If this post is already republished by the client, nothing will happen.

        :returns: republished instance of this post, or None if already republished
        :rtype: Post, or None
        """
        response = requests.post(f"{self._url}/republished",
                                 headers = self.headers)

        if response.status_code == 403:
            return None

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return Post(response.json()["data"]["id"],
                    client = self.client)  # test log in

    def remove_republish(self):
        """
        Un-republish this post. This should work on an instance of this post from any User.
        If this post is not republished, nothing will happen.

        :returns: self
        :rtype: Post
        """
        response = requests.delete(f"{self._url}/republished",
                                   headers = self.headers)

        if response.status_code == 403:
            return self

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

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
            raise TypeError(
                f"type must be one of {', '.join(valid)}, not {type}")

        params = {"type": type}

        response = requests.put(f"{self._url}/abuses",
                                headers = self.headers,
                                params = params)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

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
            raise exceptions.NotOwnContent(
                f"Post must belong to the client, but belongs to {self.author.nick}"
            )

        tags = ",".join([f"\"{tag.replace(' ', '')}\"" for tag in tags])

        data = f"tags=[{tags}]"

        response = requests.put(f"{self._url}/tags",
                                headers = self.headers,
                                data = data)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def delete(self):
        """
        Delete a post owned by the Client.

        :returns: self

        :rtype: Post
        """

        response = requests.delete(self._url, headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def pin(self):
        """
        Pin a post to the client user.
        Note that trying to pin a pinned post will return a ``403``.

        :returns: self

        :rtype: Post
        """

        response = requests.put(f"{self._url}/pinned", headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

    def unpin(self):
        """
        Unpin a post to the client user.

        :returns: self

        :rtype: Post
        """

        response = requests.delete(f"{self._url}/pinned",
                                   headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh  # test log in

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

        data = {"publish_at": int(schedule)}

        response = requests.patch(f"{self._url}",
                                  data = data,
                                  headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self  # test log in

    def set_visibility(self, visibility):
        """
        Update a delated posts visibility
        If post is not delated, nothing will happen

        :param visibility: visibility type. Can be one of (``public``, ``subscribers``)

        :type visibility: str

        :returns: self
        :rtype: Post
        """
        if not self.state == "delated":
            return None

        if visibility not in {"public", "subscribers"}:
            raise ValueError(f"visibility cannot be {visibility}")

        data = {"visibility": visibility, "tags": json.dumps(self.tags)}

        response = requests.patch(f"{self._url}",
                                  data = data,
                                  headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self  # test log in

    def read(self):
        """
        Mark this meme as read

        :returns: was this marked as read?
        :rtype: bool
        """
        return requests.put(f"{self.api}/reads/{self.id}",
                            headers = self.headers).status_code == 200

    # public generators

    @property
    def smiles(self):
        """
        :returns: generator iterating post smiles

        :rtype: generator<User>
        """
        return methods.paginated_generator(self._smiles_paginated)

    @property
    def comments(self):
        """
        :returns: generator iterating post comments

        :rtype: generator<Comment>
        """
        return methods.paginated_generator(self._comments_paginated)

    # private properties

    @property
    def _meta(self):
        type = self.type
        type = type.replace("gif_caption", "gif")
        return self.get(type, {})

    # public properties

    # authentication independant properties

    @property
    def smile_count(self):
        """
        :returns: post's smile count
        :rtype: int
        """
        if self.get("num").get("smiles"):
            return self.get("num").get("smiles")
        else:
            return self.fresh.get("num").get("smiles")

    @property
    def unsmile_count(self):
        """
        :returns: post's unsmile count
        :rtype: int
        """
        if self.get("num").get("unsmiles"):
            return self.get("num").get("unsmiles")
        else:
            return self.fresh.get("num").get("unsmiles")

    @property
    def guest_smile_count(self):
        """
        :returns: post's smile count by guests
        :rtype: int
        """
        if self.get("num").get("guest_smiles"):
            return self.get("num").get("guest_smiles")
        else:
            return self.fresh.get("num").get("guest_smiles")

    @property
    def comment_count(self):
        """
        :returns: post's comment count
        :rtype: int
        """
        if self.get("num").get("comments"):
            return self.get("num").get("comments")
        else:
            return self.fresh.get("num").get("comments")

    @property
    def view_count(self):
        """
        :returns: post's view count
        :rtype: int
        """
        if self.get("num").get("views"):
            return self.get("num").get("views")
        else:
            return self.fresh.get("num").get("views")

    @property
    def republication_count(self):
        """
        :returns: post's republication count
        :rtype: int
        """
        if self.get("num").get("republished"):
            return self.get("num").get("republished")
        else:
            return self.fresh.get("num").get("republished")

    @property
    def share_count(self):
        """
        :returns: post's share count
        :rtype: int
        """
        if self.get("num").get("shares"):
            return self.get("num").get("shares")
        else:
            return self.fresh.get("num").get("shares")

    @property
    def author(self):
        """
        :returns: post's author
        :rtype: User
        """
        data = self.get("creator")
        return User(data["id"], client = self.client, data = data)

    @property
    def source(self):
        """
        :returns: post's instance on it's original account, if a republication
        :rtype: Post
        """
        _data = self.get("source")

        if not _data:
            return None

        return Post(_data["id"], client = self.client, data = _data)

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
        return self.get("is_featured")

    @property
    def is_pinned(self):
        """
        :returns: is this post pinned on it's authors profile?
        :rtype: bool
        """
        return self.get("is_pinned")

    @property
    def is_abused(self):
        """
        :returns: was this post removed by moderators?
        :rtype: bool
        """
        return self.get("is_abused")

    @property
    def type(self):
        """
        :returns: content ype of a post
        :rtype: str
        """
        return self.get("type")

    @property
    def tags(self):
        """
        :returns: the tags of a post
        :rtype: list<str>
        """
        return self.get("tags")

    @property
    def visibility(self):
        """
        :returns: the visibility of a post
        :rtype: str (public, subscribers, ect)
        """
        return self.get("visibility")

    @property
    def state(self):
        """
        :returns: the publicication state of the post
        :rtype: str (published, ect)
        """
        return self.get("state")

    @property
    def boostable(self):
        """
        :returns: can this post be boosted?
        :rtype: bool
        """
        return self.get("can_be_boosted")

    @property
    def created_at(self):
        """
        :returns: creation date timestamp
        :rtype: int
        """
        return self.get("date_create")

    @property
    def published_at(self):
        """
        :returns: creation date timestamp
        :rtype: int
        """
        return self.get("published_at")

    @property
    def content_url(self):
        """
        :returns: url pointing to the full sized image
        :rtype: str
        """
        return self.get("url")

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

    @property
    def link(self):
        """
        :returs: this posts link
        :rtype: str
        """
        return self.get("link")

    # authentication dependant properties

    @property
    def is_republished(self):
        """
        :returns: is this post a republication?
        :rtype: bool
        """
        return self.get("is_republished")  # test log in

    @is_republished.setter
    def is_republished(self, value):
        if value:
            self.republish()
        else:
            self.remove_republish()  # test log in

    @property
    def is_smiled(self):
        """
        :returns: did I smile this post?
        :rtype: bool
        """
        return self.get("is_smiled")  # test log in

    @is_smiled.setter
    def is_smiled(self, value):
        if value:
            self.smile()
        else:
            self.remove_smile()  # test log in

    @property
    def is_unsmiled(self):
        """
        :returns: did I unsmile this post?
        :rtype: bool
        """
        return self.get("is_unsmiled")  # test log in

    @is_unsmiled.setter
    def is_unsmiled(self, value):
        if value:
            self.unsmile()
        else:
            self.remove_unsmile()  # test log in

    @visibility.setter
    def visibility(self, value):
        self.set_visibility(value)  # test log in

    @tags.setter
    def tags(self, value):
        if isinstance(value, str):
            value = [value]

        if not isinstance(value, Iterable):
            raise ValueError("value must be iterable")

        self.set_tags(list(value))  # test log in

    @is_pinned.setter
    def is_pinned(self, value):
        if value:
            self.pin()
        else:
            self.unpin()  # test log in


class Comment(mixin.ObjectMixin):
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
    def __init__(self, *args, post = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._post = post
        self.__cid = None

        if self._post == None and self._object_data_payload["cid"] == None:
            raise ValueError("This needs a post")

        self._absolute_url = f"{self.client.api}/content/{self.cid}/comments"

        self._url = f"{self.client.api}/content/{self.cid}/comments/{self.id}"

    @property
    def _object_data(self):
        if self._update or self._object_data_payload is None:
            self._update = False
            try:
                response = methods.request("get",
                                           self._url,
                                           headers = self.headers)

                self._object_data_payload = response["data"]["comment"]

            except exceptions.NotFound:
                if self._object_data_payload:
                    self._object_data_payload["is_deleted"] = True

                else:
                    raise exceptions.NotFound(
                        f"Request on {self._url} returned 404")

        return self._object_data_payload

    def __repr__(self):
        # todo image url if any
        return self.content if self.content else self.attached_post.link

    def _replies_paginated(self, limit = None, prev = None, next = None):
        limit = limit if limit else self.paginated_size

        data = methods.paginated_data(f"{self._url}/replies",
                                      "replies",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = next)

        items = [
            Comment(item["id"],
                    client = self.client,
                    data = item,
                    post = self.cid) for item in data["items"]
        ]

        return methods.paginated_format(data, items)

    # public methods

    def reply(self, text = "", post = None, user_mentions = None):
        """
        Reply to a comment.
        At least one of the parameters must be used, as users cannot post empty replys.

        :param text: Text of the reply, if any
        :param post: Post to post in the reply, if any. Can be a post id or a Post object, but the Post in reference must belong to the client creating the reply
        :param user_mentions: Users to mention, if any. Mentioned users must have their nick in the reply, and will be mentioned at the first occurance of their nick

        :type text: str
        :type post: Post or str
        :type user_mentions: list<User>

        :raises: RateLimit, TooManyMentions

        :returns: the posted reply
        :rtype: Comment
        """

        if not any((text, post, user_mentions)):
            raise exceptions.NoContent(
                "Must have at least one of (text, post, user_mentions)")

        data = {}

        if text:
            data["text"] = str(text)

        if user_mentions:
            if any([user.nick not in text for user in user_mentions]):
                raise exceptions.TooManyMentions(
                    "Not all user mentions are included in the text")

            formatted = [
                ":".join([user.id, methods.get_slice(text, user.nick)])
                for user in user_mentions
            ]
            data["user_mentions"] = ";".join(formatted)

        if post:
            if isinstance(post, str):
                post = Post(post, client = self.client)

            if post.author != self.client.user:
                raise exceptions.NotOwnContent(
                    "Users can only add ther own posts to a meme")

            data["content"] = post.id

        response = methods.request("post",
                                   f"{self._url}/replies",
                                   data = data,
                                   headers = self.headers)

        if response["data"]["id"] == "000000000000000000000000":
            raise exceptions.RateLimit(
                f"Failed to add the comment {text}. Are you posting the same comment too fast?"
            )

        return Comment(response["data"]["id"],
                       client = self.client,
                       data = response["data"]["comment"])

    def delete(self):
        """
        Delete a comment

        :returns: self

        :rtype: Comment
        """

        response = requests.delete(f"{self._absolute_url}/{self.id}",
                                   headers = self.headers)

        return self

    def smile(self):
        """
        smile a comment. If already smiled, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        methods.request("put", f"{self._url}/smiles", headers = self.headers)

        return self.fresh

    def remove_smile(self):
        """
        Remove a smile from a comment. If none exists, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        try:
            methods.request("delete",
                            f"{self._url}/smiles",
                            headers = self.headers)

        except exceptions.RepeatedAction:
            pass

        return self.fresh

    def unsmile(self):
        """
        Unsmile a comment. If already unsmiled, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        try:
            methods.request("put",
                            f"{self._url}/unsmiles",
                            headers = self.headers)

        except exceptions.RepeatedAction:
            pass

        return self.fresh

    def remove_unsmile(self):
        """
        Remove an unsmile from a comment. If none exists, nothing will happen.

        :returns: self
        :rtype: Comment
        """
        try:
            methods.request("delete",
                            f"{self._url}/unsmiles",
                            headers = self.headers)

        except exceptions.RepeatedAction:
            pass

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
            raise TypeError(
                f"type must be one of {', '.join(valid)}, not {type}")

        params = {"type": type}

        methods.request("put",
                        f"{self._url}/abuses",
                        headers = self.headers,
                        params = params)

        return self.fresh

    # public generators

    @property
    def replies(self):
        """
        :returns: generator iterating comment replies
        :rtype: generator<Comment>
        """
        if not self.depth:
            for x in methods.paginated_generator(self._replies_paginated):
                yield x
        else:
            for _comment in self.root.replies:
                if _comment.depth > self.depth and _comment.get(
                        "parent_comm_id") == self.id:
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
        value = self.get("text")
        return value if value else ""

    @property
    def cid(self):
        """
        :returns: the cid of this comment. A comments CID is the id of the post it's attached to
        :rtype: str
        """
        if type(self._post) is str:
            self._post = Post(self._post, client = self.client)

        if self._post:
            return self._post.id

        if not self.__cid:
            self.__cid = self.get("cid")

        return self.__cid

    @property
    def state(self):
        """
        :returns: the state of the comment. Top comments are state top, and all others are state normal
        :rtype: str (top, normal)
        """
        return self.get("state")

    @property
    def author(self):
        """
        :returns: the comment author
        :rtype: Use
        """
        data = self.get("user")
        return User(data["id"], client = self.client, data = data)

    @property
    def post(self):
        """
        :returns: the post that this comment is on
        :rtype: Post
        """
        return Post(self.cid, client = self.client)

    @property
    def parent(self):
        """
        :returns: direct parent of this comment, or none for root comments
        :rtype: Comment
        """
        if self.is_root:
            return None

        return Comment(self.get("parent_comm_id"),
                       client = self.client,
                       post = self.cid)

    @property
    def root(self):
        """
        :returns: this comments root parent, or self if comment is root
        :rtype: Comment
        """
        if self.is_root:
            return self

        return Comment(self.get("root_comm_id"),
                       client = self.client,
                       post = self.cid)

    @property
    def smile_count(self):
        """
        :returns: number of smiles on this comment
        :rtype: int
        """
        if self.get("num").get("smiles"):
            return self.get("num").get("smiles")
        else:
            return self.fresh.get("num").get("smiles")

    @property
    def unsmile_count(self):
        """
        :returns: number of unsmiles on this comment
        :rtype: int
        """
        if self.get("num").get("unsmiles"):
            return self.get("num").get("unsmiles")
        else:
            return self.fresh.get("num").get("unsmiles")

    @property
    def reply_count(self):
        """
        :returns: number of replies on this comment
        :rtype: int
        """
        if self.get("num").get("replies"):
            return self.get("num").get("replies")
        else:
            return self.fresh.get("num").get("replies")

    @property
    def created_at(self):
        """
        :returns: creation date timestamp
        :rtype: int
        """
        return self.get("date")

    @property
    def depth(self):
        """
        :returns: the depth of this comment
        :rtype: int
        """
        if self.is_root:
            return 0

        return self.get("depth")

    @property
    def is_root(self):
        """
        :returns: is this comment a top level (root) comment?
        :rtype: bool
        """
        return not self.get("is_reply")

    @property
    def is_edited(self):
        """
        :returns: has this comment been deleted?
        :rtype: bool
        """
        return self.get("is_edited")

    @property
    def attached_post(self):
        """
        :returns: the attached post, if any
        :rtype: Post, or None
        """
        data = self.get("attachments")["content"]

        if len(data) == 0:
            return None

        return Post(data[0]["id"], client = self.client, data = data[0])

    @property
    def user_mentions(self):
        """
        :returns: a list of mentioned users, if any
        :rtype: list<User>
        """
        data = self.get("attachments")["mention_user"]

        return [User(item["user_id"], client = self.client) for item in data]

    # authentication dependant properties

    @property
    def is_smiled(self):
        """
        :returns: did I smile this comment?
        :rtype: bool
        """
        return self.get("is_smiled")

    @property
    def is_unsmiled(self):
        """
        :returns: did I unsmile this comment?
        :rtype: bool
        """
        return self.get("is_unsmiled")


class Notification:
    """
    General purpose notification object.
    Used to represent any notification recieved by a client

    :param data: iFunny api response that makes up the data
    :param client: iFunny client that the notification belongs to

    :type data: dict
    :type client: Client
    """
    def __init__(self, data, client = mixin.ClientBase()):
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

        return User(data["id"], client = self.client, data = data)

    @property
    def post(self):
        """
        :returns: the post attatched to a notification.
        :rtype: Post, or None
        """
        data = self.__data.get("content")

        if not data:
            return None

        return Post(data["id"], client = self.client, data = data)

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
            return Comment(data["id"],
                           client = self.client,
                           data = data,
                           post = post)

        return Comment(data["id"],
                       client = self.client,
                       data = data,
                       post = post)

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


class Channel(mixin.ObjectMixin):
    def __init__(self, id, client = mixin.ClientBase(), data = {}):
        """
        Object for ifunny explore channels.

        :param id: id of the feed
        :param client: Client that is requesting the feed
        :param data: json data of this feed

        :type id: str
        :type client: Client
        :type data: dict
        """
        super().__init__(id, client = client, data = data)
        self._feed_url = f"{self.client.api}/channels/{self.id}/items"

    def get(self, key, default = None):
        # TODO: surely we can get updated information from somewhere?
        return self._object_data_payload.get(key, default)

    def _feed_paginated(self, limit = 30, next = None, prev = None):
        data = methods.paginated_data(self._feed_url,
                                      "content",
                                      self.headers,
                                      limit = limit,
                                      prev = prev,
                                      next = prev)

        items = [
            Post(item["id"], client = self.client, data = item)
            for item in data["items"]
        ]

        return methods.paginated_format(data, items)

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
        return methods.paginated_generator(self._feed_paginated)


class Digest(mixin.ObjectMixin):
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
    def _object_data(self):
        if self._update or self._object_data_payload is None:
            self._update = False

            params = {
                "contents": int(self._contents),
                "comments": int(self._comments)
            }

            response = requests.get(self._url,
                                    headers = self.headers,
                                    params = params)

            if response.status_code == 403:
                self._object_data_payload = {}
                return self._object_data_payload

            try:
                self._object_data_payload = response.json()["data"]
            except KeyError:
                raise exceptions.BadAPIResponse(
                    f"{response.url}, {response.text}")

        return self._object_data_payload

    def __repr__(self):
        return self.title

    def __len__(self):
        return self.post_count

    # public methods

    def read(self, count = None):
        """
        Mark posts in this digest as read.
        Will mark all read by default

        :param count: number of posts to mark as read

        :type count: int

        :returns: self
        :rtype: Digest
        """
        count = count if count else self.unread_count
        response = requests.post(f"{self._url}/reads/{count}",
                                 headers = self.headers)

        if response.status_code != 200:
            raise exceptions.BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh

    # public properties

    @property
    def feed(self):
        """
        :returns: generator for posts that are in this digest
        :rtype: generator<Post>
        """
        self._contents = True

        for data in self.get("items"):
            yield Post(data["id"], client = self.client, data = data)

    @property
    def comments(self):
        """
        :returns: subscriber comments that are in this digest
        :rtype: generator<Comment>
        """
        self._comments = True

        for data in self.get("subscription_comments"):
            post = Post(data["contentId"], client = self.client)
            yield Comment(data["commentId"], client = self.client,
                          post = post)  # test log in

    @property
    def title(self):
        """
        :returns: the title of this digest
        :rtype: str
        """
        return self.get("title")

    @property
    def smile_count(self):
        """
        :returns: number of smiles in this digest
        :rtype: int
        """
        return self.get("likes")

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
        return self.get("comments")

    @property
    def post_count(self):
        """
        :returns: number of posts in this digest
        :rtype: int
        """
        return self.get("item_count")

    @property
    def unread_count(self):
        """
        :returns: number of unread posts in this digest
        :rtype: int
        """
        return self.get("unreads")  ##

    @property
    def count(self):
        """
        :returns: index of this digest
        :rtype: int
        """
        return self.get("count")

    @property
    def index(self):
        """
        Alias for ``Digest.count``
        """
        return self.count
