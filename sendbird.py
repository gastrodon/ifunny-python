import websocket, json, time, threading, requests

class Socket:
    def __init__(self, client):
        self.client = client
        self.handler = Handler(client)
        self.socket_url = "wss://ws-us-1.sendbird.com"
        self.sendbird_url = "https://api-p.sendbird.com"
        self.route = "AFB3A55B-8275-4C1E-AEA8-309842798187"
        self.active = False
        self.socket = None
        self.socket_thread = None

    def on_open(self):
        print("ws opened")

    def on_close(self):
        print("ws closed")

    def on_ping(self, data):
        print("ws pinged")

    def on_pong(self, data):
        print(f"The server sent back {data}")

    def on_message(self, data):
        return self.handler.resolve(data)

    def start(self):
        route = requests.get(f"{self.sendbird_url}/routing/{self.route}").json()
        self.socket_url = route["ws_server"]

        self.socket = websocket.WebSocketApp(
            f"{self.socket_url}?dp=Android&pv=21&sv=3.0.55&ai={self.route}&user_id={self.client.id}&access_token={self.client.messenger_token}",
            on_message = self.on_message,
            on_open = self.on_open,
            on_close = self.on_close,
            on_ping = self.on_ping
        )

        self.socket_thread = threading.Thread(target = self.socket.run_forever, kwargs = {"ping_interval": 15})
        self.socket_thread.start()
        self.active = True

    def send(self, data):
        return self.socket.send(data)

class Handler:
    def __init__(self, client):
        self.client = client
        self.matches = {
            "PING": self.ping
        }

    def resolve(self, data):
        return self.matches.get(data[:4], self.default)(data[:4], json.loads(data[4:]))

    def default(self, key, data):
        print(f"Don't know about {key}")
        return

    def ping(self, key, data):
        id = data["id"]
        timestamp = int(time.time() * 1000)
        print("will PONG")

        data = json.dumps({
            "id": id,
            "ts": timestamp,
            "sts": timestamp
        })

        return client.socket.send(f"PONG{data}")
