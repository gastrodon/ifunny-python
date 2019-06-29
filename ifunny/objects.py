import json, time, random
from ifunny.utils import determine_mime

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

        self.sendbird_url = data["channel_url"]
        self.id = data["channel_id"]
        self.type = data["channel_type"]

class MessageContext:
    def __init__(self, client, data):
        self.client = client
        self.socket = self.client.socket
        self.commands = self.client.commands
        self.channel_url = data["channel_url"]
        self.message = data["message"]

    def send(self, message):
        response_data = {
            "channel_url"   : self.channel_url,
            "message"       : message
        }

        return self.socket.send(f"MESG{json.dumps(response_data, separators = (',', ':'))}\n")


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
                    "real_height"   : int(780 if type is "tall" else 780 * lower_ratio),
                    "real_width"    : int(780 if type is "wide" else 780 * lower_ratio),
                    "height"        : width,
                    "width"         : height,
                }
            ]
        }

        return self.socket.send(f"FILE{json.dumps(response_data, separators = (',', ':'))}\n")

    @property
    def prefix(self):
        return self.client.prefix
