import json, time

from ifunny import objects


class Handler:
    def __init__(self, client):
        self.client = client
        self.events = {}

        self.channel_update_codes = {
            10020: self._on_invite,
            10001: self._on_user_exit,
            10000: self._on_user_join
        }

        self.matches = {
            "PING": self._on_ping,
            "MESG": self._on_message,
            "LOGI": self._on_connect,
            "SYEV": self._on_channel_update,
            "FILE": self._on_file
        }

    def resolve(self, data):
        key, data = data[:4], json.loads(data[4:])
        self.matches.get(key, self._default_match)(key, data)

    def get_ev(self, key):
        return self.events.get(key, self._default_event)

    # websocket hook defaults

    def _default_match(self, key, data):
        return

    def _default_event(self, *args):
        exec = self.events.get("on_default")
        if exec:
            exec(args)

    # private hooks

    def _on_disconnect(self):
        self.get_ev("on_disconnect")()

    def _on_message(self, key, data):
        if data["user"]["name"] == self.client.nick:
            return

        message = objects.Message(data["msg_id"],
                                  data["channel_url"],
                                  self.client,
                                  data = data)

        message.invoked = self.client.resolve_command(message)
        self.get_ev("on_message")(message)

    def _on_file(self, key, data):
        if data["user"]["name"] == self.client.nick:
            return

        message = objects.Message(data["msg_id"],
                                  data["channel_url"],
                                  self.client,
                                  data = data)
        self.get_ev("on_message")(message)

    def _on_connect(self, key, data):
        if data.get("key"):
            self.client.messenger_token = data["key"]
        self.client.socket.connected = True
        self.get_ev("on_connect")(
            data)  # TODO: consider using an object for the data

    def _on_ping(self, key, data):
        self.get_ev("on_ping")(data)

        timestamp = int(time.time() * 1000)

        data = json.dumps({
            "id": data["id"],
            "ts": timestamp,
            "sts": timestamp
        })

        return client.socket.send(f"PONG{data}\n")

    def _on_channel_update(self, key, data):
        chat = objects.Chat(data["channel_url"], self.client)
        self.channel_update_codes.get(data["cat"], self._default_event)(data)
        self.get_ev("on_channel_update")(chat)

    def _on_invite(self, update):
        invite = objects.ChatInvite(update, self.client)
        if self.client.user in invite.invitees:
            return self.get_ev("on_invite")(invite)

        return self.get_ev("on_invite_broadcast")(invite)

    def _on_user_exit(self, data):
        chat = objects.Chat(data["channel_url"], self.client)
        user = objects.User(data["data"]["user_id"], client = self.client)
        self.get_ev("on_user_exit")(user, chat)

    def _on_user_join(self, data):
        chat = objects.Chat(data["channel_url"], self.client)
        user = objects.User(data["data"]["user_id"], client = self.client)
        self.get_ev("on_user_join")(user, chat)

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

    def __call__(self, *data):
        self.method(*data)
        return self


"""
events allowed:
    on_message                  -> (objects.Message):           a chat message is recieved
    on_channel_update           -> (objects.Chat):           something is done to update a chat that the client can see
    on_invite (10020)           -> (objects.ChatInvite):     the client is sent an invite
    on_invite_broadcast (10020) -> (objects.ChatInvite):     an invite is broadcast to people that are not the client
    on_user_join (10000)        -> (objects.User, objects.Chat):     a user joins the chat
    on_user_exit (10001)        -> (objects.User, objects.Chat):     a user leaves or is kicked from the chat
    on_ping                     -> (json data):         we are pinged
    on_connect                  -> (json data):         ifunny achnowledges our websocket connection
    on_default                  -> (any):               websocket messages matches no events that the client has implemented
"""
