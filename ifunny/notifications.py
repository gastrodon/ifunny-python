import json
from ifunny.objects import Peer, Post, Comment

class Notification:
    def __init__(self, data, client):
        self.type = data["type"]
        self.client = client
        self.timestamp = data["date"]

        self.__data = data
        self.__user = None
        self.__content = None
        self.__comment = None

    @property
    def user(self):
        if not self.__user and "user" in self.__data:
            self.__user = Peer(self.__data["user"], self.client)

        return self.__creator

    @property
    def content(self):
        if not self.__content and "content" in self.__data:
            self.__content = Post(self.__data["creator"], self.client)

        return self.__comment

    @property
    def comment(self):
        if not self.__comment and "comment" in self.__data:
            self.__comment = Comment(self.__data["comment"], self.client)

        return self.__comment

class CommentNotification(Notification):
    def __init__(self, data, client):
        super().__init__(data, client)

        self.id = data["comment"]["id"]
        self.cid = data["comment"]["cid"]
        self.is_reply = data["comment"]["is_reply"]
        self.smiles = data["comment"]["num"]["smiles"]


_match = {
"comment": CommentNotification
}

def resolve_notification(data, client):
    return _match.get(data["type"], Notification)(data, client)
