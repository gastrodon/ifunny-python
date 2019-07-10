import json, requests
from time import time

from ifunny.objects import Message, Invite

class Handler:
    def __init__(self, client):
        self.client = client
        self.events = {}

        self.matches = {
            "PING": self._on_ping,
            "MESG": self._on_message,
            "LOGI": self._on_connect,
            "SYEV": self._on_new_channel
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

        message = Message(data, self.client)

        self.events.get("on_message", self.default_event)(message)
        self.client.resolve_command(message)

    def _on_connect(self, key, data):
        self.client.sendbird_session_key = data["key"]
        self.client.socket.connected = True
        self.events.get("on_connect", self.default_event)(data) # TODO: consider using an object for the data

    def _on_ping(self, key, data):
        self.events.get("on_ping", self.default_event)(data)

        timestamp = int(time() * 1000)

        data = json.dumps({
            "id"    : data["id"],
            "ts"    : timestamp,
            "sts"   : timestamp
        })

        return client.socket.send(f"PONG{data}\n")

    def _on_new_channel(self, key, data):
        invite = Invite(data, self.client)
        self.events.get("on_new_channel", self.default_event)(invite)

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
