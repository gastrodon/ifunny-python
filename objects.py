import json

class Peer:
    def __init__(self, data, client):
        self.client = client
        
        self.nick = data["nick"]
        self.id = data["id"]
        self.banned = data["is_banned"]
        self.deleted = data["is_deleted"]
        self.verified = data["is_verified"]

class Post:
    def __init__(self, data, client):
        self.client = client
        self.creator = Peer(data["creator"], client)

        self.type = data["type"]
        self.id = data["id"]
        self.tags = data["tags"]
        self.smiles = data["num"]["smiles"]
        self.unsmiles = data["num"]["unsmiles"]
        self.comments = data["num"]["comments"]
        self.views = data["num"]["views"]
        self.repubs = data["num"]["republished"]
