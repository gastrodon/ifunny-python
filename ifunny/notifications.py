import json
from ifunny.objects import User, Post, Comment

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
