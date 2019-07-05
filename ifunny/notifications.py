import json
from ifunny.objects import User, Post, Comment

class Notification:
    def __init__(self, data, client):
        self.client = client
        self.type = data["type"]

        self.__data = data

    @property
    def user(self):
        data = self.__data.get("user")

        if not data:
            return None

        return User(data["id"], self.client, data = data)

    @property
    def post(self):
        data = self.__data.get("content")

        if not data:
            return None

        return Post(data["id"], self.client, data = data)

    @property
    def comment(self):
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
        return self.__data.get("date")

    @property
    def smile_count(self):
        return self.__data.get("smiles")
