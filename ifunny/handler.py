import json, random

class Handler:
    def __init__(self, client):
        self.client = client
        self.matches = {
            "PING": self.on_ping,
            "MESG": self.on_message
        }

    def resolve(self, data):
        key, data = data[:4],  json.loads(data[4:])
        return self.matches.get(key, self.default)(key, data)

    def default(self, key, data):
        return

    def on_ping(self, key, data):
        id = data["id"]
        timestamp = int(time.time() * 1000)

        data = json.dumps({
            "id": id,
            "ts": timestamp,
            "sts": timestamp
        })

        return client.socket.send(f"PONG{data}")

    def on_message(self, key, data):
        print("message sent")
        print(json.dumps(data))
        return self.client.commands.resolve_execute(MessageContext(self.client, data))

class MessageContext:
    def __init__(self, client, data, _):
        self.client = client
        self.socket = self.client.socket
        self.commands = self.client.commands
        self.channel_url = data["channel_url"]
        self.message = data["message"]

    def send(self, message):
        print("will send")
        response_data = {
            "channel_url"   : self.channel_url,
            "message"       : message
        }

        return self.socket.send(f"MESG{json.dumps(response_data, separators = (',', ':'))}\n")

    @property
    def prefix(self):
        return self.commands.get_prefix(self)
