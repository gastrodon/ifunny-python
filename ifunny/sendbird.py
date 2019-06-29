import websocket, json, time, threading, requests

class Socket:
    def __init__(self, client = None):
        self.client = client
        self.socket_url = "wss://ws-us-1.sendbird.com"
        self.sendbird_url = "https://api-p.sendbird.com"
        self.route = "AFB3A55B-8275-4C1E-AEA8-309842798187"
        self.active = False
        self.socket = None
        self.socket_thread = None

    def on_open(self):
        return

    def on_close(self):
        print("closed")
        return

    def on_ping(self, data):
        return

    def on_pong(self, data):
        return

    def on_message(self, data):
        print(data)
        return
        return self.client.handler.resolve(data)

    def start(self):
        route = requests.get(f"{self.sendbird_url}/routing/{self.route}").json()
        self.socket_url = route["ws_server"]

        websocket.enableTrace(self.client.socket_trace)
        self.socket = websocket.WebSocketApp(
            f"{self.socket_url}?dp=Android&pv=21&sv=3.0.55&ai={self.route}&user_id={self.client.id}&access_token={self.client.messenger_token}",
            on_message = self.on_message,
            on_open = self.on_open,
            on_close = self.on_close,
            on_ping = self.on_ping
        )

        self.socket.run_forever(ping_interval = 15)
        return

        self.socket_thread = threading.Thread(target = self.socket.run_forever, kwargs = {"ping_interval": 15})
        self.socket_thread.start()
        self.active = True

    def send(self, data):
        self.socket.send(data)
