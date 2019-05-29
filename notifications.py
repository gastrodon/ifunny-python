import json
from objects import Peer, Post

class Notification:
    def __init__(self, data, client):
        self.client = client
        self.timestamp = data["date"]
        self.type = None

class CommentNotification(Notification):
    def __init__(self, data, client):
        super().__init__(data, client)
        self.type = "comment"
        self.post = Post(data["content"], client)
        self.from_user = Peer(data["user"], client)

        self.content = data["comment"]["text"]
        self.id = data["comment"]["id"]
        self.cid = data["comment"]["cid"]
        self.is_reply = data["comment"]["is_reply"]
        self.smiles = data["comment"]["num"]["smiles"]

_match = {
"comment": CommentNotification
}

def resolve_notification(data, client):
    return _match.get(data["type"], Notification)(data, client)
