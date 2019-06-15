import json

class Handler:
    def __init__(self, client):
        self.client = client
        self.matches = {
            "PING": self.on_ping,
            "MESG": self.on_message
        }

    def resolve(self, data):
        return self.matches.get(data[:4], self.default)(data[:4], json.loads(data[4:]))

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
        return
