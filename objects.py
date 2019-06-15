import json

class Peer:
    def __init__(self, data, client):
        self.client = client

        self.nick = data["nick"]
        self.id = data["id"]
        self.banned = data["is_banned"]
        self.deleted = data["is_deleted"]
        self.verified = data["is_verified"]

    def __repr__(self):
        return self.nick

class Post:
    def __init__(self, data, client):
        self.client = client
        self.__data = data
        self.__creator = None

        self.type = data["type"]
        self.id = data["id"]
        self.tags = data["tags"]
        self.smiles = data["num"]["smiles"]
        self.unsmiles = data["num"]["unsmiles"]
        self.comments = data["num"]["comments"]
        self.views = data["num"]["views"]
        self.repubs = data["num"]["republished"]

    @property
    def creator(self):
        if not self.__creator:
            self.__creator = Peer(self.__data["creator"], self.client)

        return self.__creator

class Comment:
    def __init__(self, data, client):
        self.client = client
        self.__data = data
        self.__creator = None
        # v4/users/data["id"] links to the user data

        self.text = data["text"]
        self.id = data["id"]
        self.cid = data["cid"]
        self.state = data["state"] #top comments have the state top, others have normal
        self.is_reply = data["is_reply"]
        self.smiles = data["num"].get("smiles", 0)
        self.unsmiles = data["num"].get("unsmiles", 0)

    def __repr__(self):
        return self.text

class ChatChannel:
    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.channel_url = 
