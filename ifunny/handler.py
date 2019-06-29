import json, requests, asyncio, decorator
from time import time

from ifunny.objects import MessageContext

class Handler:
    def __init__(self):
        self.client = None
        self.events = {}

        self.matches = {
            "PING": self._on_ping,
            "MESG": self._on_message,
            "LOGI": self._on_ws_connect
        }

    async def resolve(self, data):
        print("inside handler")
        key, data = data[:4], json.loads(data[4:])
        try:
            await self.matches.get(key, self.default_match)(key, data)
        except Exception as e:
            print(e)
        print("handler completed")

    # websocket hook defaults

    async def default_match(self, key, data):
        return

    async def default_event(self, *args):
        return

    # private hooks

    async def _on_message(self, key, data):
        if data["user"]["name"] == self.client.nick:
            return

        await self.events.get("on_message", self.default_event)(data) # TODO: use a message object here

        ctx = MessageContext(self.client, data)
        await self.client.resolve_command(ctx)

    async def _on_ws_connect(self, key, data):
        print("in _on_ws_connect")
        self.client.sendbird_session_key = data["key"]
        self.client.socket.connected = True

        await self.events.get("on_ws_connect", self.default_event)(data) # TODO: consider using an object for the data
        print("exit _on_ws_connect")

    async def _on_ping(self, key, data):
        timestamp = int(time() * 1000)

        data = json.dumps({
            "id"    : data["id"],
            "ts"    : timestamp,
            "sts"   : timestamp
        })

        return client.socket.send(f"PONG{data}")

    # public decorators

    @decorator.decorator
    async def add(self, name = None):
        def _inner(coro):
            _name = name if name else coro.__name__
            self.events[_name] = coro

        return _inner
