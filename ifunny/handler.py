import json, requests
from time import time

from ifunny.objects import MessageContext

class Handler:
    def __init__(self):
        self.client = None
        self.events = {}

        self.matches = {
            "PING": self._on_ping,
            "MESG": self._on_message,
            "LOGI": self._on_connect
        }

    def resolve(self, data):
        key, data = data[:4], json.loads(data[4:])
        self.matches.get(key, self.default_match)(key, data)

    # websocket hook defaults

    def default_match(self, key, data):
        return

    def default_event(self, *args):
        return

    # private hooks

    def _on_message(self, key, data):
        if data["user"]["name"] == self.client.nick:
            return

        ctx = MessageContext(self.client, data)

        self.events.get("on_message", self.default_event)(ctx) # TODO: use a message object here
        self.client.resolve_command(ctx)

    def _on_connect(self, key, data):
        print("connected default")
        self.client.sendbird_session_key = data["key"]
        self.client.socket.connected = True
        self.events.get("on_connect", self.default_event)(data) # TODO: consider using an object for the data

    def _on_ping(self, key, data):
        timestamp = int(time() * 1000)

        data = json.dumps({
            "id"    : data["id"],
            "ts"    : timestamp,
            "sts"   : timestamp
        })

        return client.socket.send(f"PONG{data}")

    # public decorators

    def add(self, name = None):
        def _inner(method):
            _name = name if name else method.__name__
            self.events[_name] = method

        return _inner

class Event:
    def __init__(self, method, name):
        self.method = method
        self.name = name
        self.help = self.method.__doc__

    def __call__(self, data):
        return self.method(data)
