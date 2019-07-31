import json, time, requests, threading

from ifunny.util.methods import determine_mime, paginated_data_sb, paginated_generator, paginated_params
from ifunny.util.exceptions import ChatNotActive, NotOwnContent, BadAPIResponse, Forbidden

from ifunny.objects._main_app import ObjectMixin, User

class SendbirdMixin(ObjectMixin):
    """
    Mixin class for sendbird objects.
    Used to implement common methods, subclass to ObjectMixin

    :param id: id of the object
    :param client: Client that the object belongs to
    :param data: A data payload for the object to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, id, client, data = None, paginated_size = 30):
        super().__init__(id, client, data = data, paginated_size = paginated_size)

    @property
    def _account_data(self):
        if self._update or self._account_data_payload is None:
            if not self.client.sendbird_session_key:
                raise ChatNotActive("Chat must have been activated to get sendbird api token")

            self._update = False
            response = requests.get(self._url, headers = self.client.sendbird_headers)

            if response.status_code == 403:
                self._account_data_payload = {}
                return self._account_data_payload

            try:
                self._account_data_payload = response.json()
            except KeyError:
                raise BadAPIResponse(f"{response.url}, {response.text}")

        return self._account_data_payload

class Chat(SendbirdMixin):
    """
    iFunny Chat object

    :param id: channel_url of the Chat. ``Chat.channel_url`` is aliased to this value, though ``id`` is more consistent with other mixin objects and how they update themselves.
    :param client: Client that the Chat belongs to
    :param data: A data payload for the Chat to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_url = self.id
        self._url = f"{self.client.sendbird_api}/group_channels/{self.id}"

    def __repr__(self):
        return self.title

    def _members_paginated(self, limit = None, next = None):
        limit = limit if limit else self.client.paginated_size

        data = paginated_data_sb(
            f"{self._url}/members", "members", self.client.sendbird_headers,
            limit = limit, next = next
        )

        data["items"] = [ChatUser(member["user_id"], self.client, self, sb_data = member) for member in data["items"]]

        return data

    def _messages_paginated(self, limit = None, next = None):
        limit = limit if limit else self.client.paginated_size
        next = next if next else int(time.time() * 1000)

        params = {
            "prev_limit": limit,
            "message_ts": next,
            "include"   : False,
            "is_sdk"    : True,
            "reverse"   : True
        }

        response = requests.get(f"{self._url}/messages", params = params, headers = self.client.sendbird_headers)

        if response.status_code != 200:
            raise BadAPIResponse(f"requesting {response.url} failed\n{response.text}")

        data = response.json()["messages"]
        next_ts = data[::-1][0]["created_at"]
        items = [Message(message["message_id"], message["channel_url"], self.client) for message in data]

        return {
            "items": items,
            "paging": {
                "prev": None,
                "next": next_ts
            }
        }

    def _wait_to_set_frozen(self, wait, state, callback = None):
        time.sleep(wait)

        if self.fresh.frozen:
            self.frozen = state

        if callback:
            callback(self)

    # public methods

    def add_operator(self, user):
        """
        Add an operator toi a Chat

        :params user: operator to add

        :type user: User or ChatUser

        :returns: fresh list of this chat's operators
        :rtype: List<ChatUser>
        """
        data = {
            "operators" : user.id
        }

        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}/operators", data = data, headers = self.client.headers)

        if response.status_code == 403:
            raise Forbidden("You cannot modify the operators of this chat")

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh.operators

    def remove_operator(self, user):
        """
        Remove an operator from a Chat

        :params user: operator to remove

        :type user: User or ChatUser

        :returns: fresh list of this chat's operators
        :rtype: List<ChatUser>
        """
        data = {
            "operators" : user.id
        }

        response = requests.delete(f"{self.client.api}/chats/channels/{self.channel_url}/operators", data = data, headers = self.client.headers)

        if response.status_code == 403:
            raise Forbidden("You cannot modify the operators of this chat")

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self.fresh.operators

    def join(self):
        """
        Join this chat

        :returns: did this client join successfuly?
        :rtype: bool
        """
        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}/members", headers = self.client.headers)

        return True if response.status_code == 200 else False

    def leave(self):
        """
        Leave this chat

        :returns: did this client leave successfuly?
        :rtype: bool
        """
        response = requests.delete(f"{self.client.api}/chats/channels/{self.channel_url}/members", headers = self.client.headers)

        return True if response.status_code == 200 else False

    def read(self):
        """
        Mark messages in a chat as read.

        :returns: self
        :rtype: Chat
        """
        if not self.client.socket.active:
            raise ChatNotActive("The chat socket has not been started")

        message_data = {
            "channel_url"   : self.channel_url,
            "req_id"        : self.client.next_req_id
        }

        self.client.socket.send(f"READ{json.dumps(message_data, separators = (',', ':'))}\n")
        return self

    def invite(self, user):
        """
        Invite a user or users to a chat.

        :param user: User or list<User> of invitees

        :type user: User, or list<User>

        :returs: self
        :rtype: Chat
        """

        data = json.dumps({
            "user_ids"  : [user.id] if isinstance(user, User) else [u.id for u in users]
        })

        response = requests.post(f"{self._url}/invite", data = data, headers = self.client.sendbird_headers)

        if response.status_code == 403:
            raise Forbidden("You cannot invite users to this chat")

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self

    def kick(self, user):
        """
        Kick a member from a group

        :param user: User to kick
        :type user: User

        :return: self
        :rtype: Chat
        """
        data = {
            "members": user.id
        }

        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}/kicked_members", data = data, headers = self.client.headers)

        if response.status_code == 403:
            raise Forbidden("You must be an operator or admin to kick members")

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self

    def freeze(self, until = 0, callback = None):
        """
        Freeze a Chat, and set the update flag.

        :param until: time in seconds to wait to unfreeze. If 0, there will be no unfreezing
        :param callback: method to call when unfrozen, must accept single argument for Chat

        :type until: int
        :type callback: callable, or None

        :returs: self
        :rtype: Chat
        """

        self.frozen = True

        if until and isinstance(until, int):
            threading.Thread(target = self._wait_to_set_frozen, args = [until, False], kwargs = {"callback": callback}).start()

        return self.fresh

    def unfreeze(self, until = 0, callback = None):
        """
        Freeze a Chat, and set the update flag.

        :param until: time in seconds to wait to unfreeze. If 0, there will be no unfreezing
        :param callback: method to call when unfrozen, must accept single argument for Chat

        :type until: int
        :type callback: callable, or None

        :returs: self
        :rtype: Chat
        """

        self.frozen = False

        if until and isinstance(until, int):
            threading.Thread(target = self._wait_to_set_frozen, args = [until, True], kwargs = {"callback": callback}).start()

        return self.fresh

    def send_message(self, message, read = False):
        """
        Send a text message to a chat.

        :param message: text that you will send
        :param read: do we mark the chat as read?

        :type message: str
        :type read: bool

        :raises: ChatNotActive if the attached client has not started the chat socket

        :returns: self
        :rtype: Chat
        """
        if not self.client.socket.active:
            raise ChatNotActive("The chat socket has not been started")

        message_data = {
            "channel_url"   : self.channel_url,
            "message"       : message,
            #"req_id"        : self.client.next_req_id
        }

        self.client.socket.send(f"MESG{json.dumps(message_data, separators = (',', ':'))}\n")

        if read:
            self.read()

        return self

    def send_image_url(self, image_url, width = 780, height = 780, read = False):
        """
        Send an image to a chat from a url source.

        :param image_url: url where the image is located. This should point to the image itself, not a webpage with an image
        :param width: width of the image in pixels
        :param height: heigh of the image in pixels
        :param read: do we mark the chat as read?

        :type image_url: str
        :type width: int
        :type height: int
        :type read: bool

        :raises: ChatNotActive if the attached client has not started the chat socket

        :returns: self
        :rtype: Chat
        """
        if not self.client.socket.active:
            raise ChatNotActive("The chat socket has not been started")

        lower_ratio = min([width / height, height / width])
        type = "tall" if height >= width else "wide"
        mime = determine_mime(image_url)

        response_data = {
            "channel_url"   : self.channel_url,
            "url"           : image_url,
            "name"          : f"botimage",
            "type"          : mime,
            "thumbnails"    : [
                {
                    "url"           : image_url,
                    "real_height"   : int(780 if type == "tall" else 780 * lower_ratio),
                    "real_width"    : int(780 if type == "wide" else 780 * lower_ratio),
                    "height"        : width,
                    "width"         : height,
                }
            ]
            #"req_id": self.client.next_req_id
        }

        self.client.socket.send(f"FILE{json.dumps(response_data, separators = (',', ':'))}\n")

        if read:
            self.read()

        return self

    # public generators

    @property
    def members(self):
        """
        :returns: generator to iterate through chat members
        :rtype: generator<ChatUser>
        """
        return paginated_generator(self._members_paginated)

    @property
    def messages(self):
        """
        :returns: generator to iterate through chat messages
        :rtype: generator<Message>
        """
        return paginated_generator(self._messages_paginated)

    # public properties

    @property
    def _data(self):
        _json = json.loads(self._get_prop("data", "{}")).get("chatInfo", {})

        return _json

    @property
    def send(self):
        """
        :returns: this classes send_message method
        :rtype: function
        """
        return self.send_message

    @property
    def admins(self):
        """
        :returns: list of chat admins, if group
        :rtype: List<ChatUser>, or None
        """
        data = self._data.get("chatInfo", {}).get("adminsIdList")

        if not data:
            return None

        return [ChatUser(id, self.client, self) for id in data]

    @property
    def operators(self):
        """
        :returns: list of chat operators, if group
        :rtype: List<ChatUser>, or None
        """
        data = self._data.get("chatInfo", {}).get("operatorsIdList")

        if not data:
            return None

        return [ChatUser(id, self.client, self) for id in data]

    @property
    def title(self):
        """
        :returns: the title of this chat
        :rtype: str
        """
        _title = self._get_prop("title")
        return _title if _title else self._get_prop("channel").get("name")

    @title.setter
    def title(self, value):
        data = {
            "title": str(value),
            "description": self.description
        }

        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}", data = data, headers = self.client.headers)
        self._update = True

    @property
    def name(self):
        """
        Alias for Chat.title
        """
        return self.title

    @property
    def created(self):
        """
        :returns: timestamp of this chats creation data
        :rtype: int
        """
        return self._get_prop("created_at")

    @property
    def description(self):
        """
        :returns: admin defined description of the chat, if group
        :rtype: str, or None
        """
        _desc = self._get_prop("description")
        return _desc if _desc else self._data.get("description")

    @description.setter
    def description(self, value):
        data = {
            "title": self.title,
            "description": str(value)
        }

        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}", data = data, headers = self.client.headers)
        self._update = True

    @property
    def frozen(self):
        """
        :returns: is this chat frozen? Assumes False if attribute cannot be queried
        :rtype: bool
        """
        return self._data.get("chatInfo", {}).get("frozen")

    @frozen.setter
    def frozen(self, val):
        """
        Freeze or unfreeze a Chat
        """
        if not isinstance(val, bool):
            raise TypeError("Value should be bool")

        data = f"is_frozen={str(val).lower()}"

        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}", headers = self.client.headers, data = data)

    @property
    def type(self):
        """
        :returns: the type of this group. Can be ``group``, ``opengroup``, ``chat``
        :rtype: str
        """
        return self._get_prop("custom_type")

    @property
    def direct(self):
        """
        :returns: is this chat a private message chat?
        :rtype: bool
        """
        return self.type == "chat"

    @property
    def private(self):
        """
        :returns: is this chat a private group?
        :rtype: bool
        """
        return self.type == "group"

    @property
    def public(self):
        """
        :returns: is this chat a public group?
        :rtype: bool
        """
        return self.type == "opengroup"

    @property
    def member_count(self):
        """
        :returs: number of members in this chat
        :rtype: int
        """
        return self._get_prop("member_count")

    # Authentication dependant properties

    @property
    def muted(self):
        """
        :returns: is this chat muted by the client?
        :rtype: bool
        """
        return self._get_prop("is_muted")

class ChatUser(User):
    """
    A User attatched to a chat.
    takes the same params as a User, with an extra set

    :param chat: Chat that this user is in
    :param sb_data: A sendbird data payload for the user to pull from before requests

    :type chat: Chat
    :type sb_data: dict
    """
    def __init__(self, id, client, chat, *args, sb_data = None, **kwargs):
        super().__init__(id, client, *args, **kwargs)
        self._sb_url = chat._url
        self._sb_data_payload = sb_data
        self.__chat = chat

    def _sb_prop(self, key, default = None, force = False):
        if not self._sb_data.get(key, None) or force:
            self._update = True

        return self._sb_data.get(key, default)

    # public methods

    def kick(self):
        """
        Kick a member from a group

        :return: self
        :rtype: ChatUser
        """
        data = {
            "members": self.id
        }

        response = requests.put(f"{self.client.api}/chats/channels/{self.chat.channel_url}/kicked_members", data = data, headers = self.client.headers)

        if response.status_code == 403:
            raise Forbidden("You must be an operator or admin to kick members")

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        return self

    @property
    def _sb_data(self):
        if self._update or self._sb_data_payload is None:
            self._update = False

            members = [member for member in self.chat._account_data.get("members") if member["user_id"] == self.id]

            if not len(members):
                members = [{}]

            self._sb_data_payload = members[0]

        return self._sb_data_payload

    @property
    def state(self):
        """
        :returns: Is this member invited (pending join), or joined?
        :rtype: str
        """
        return self._sb_prop("state")

    @property
    def last_online(self):
        """
        :returns: timestamp of whne this user was last online
        :rtype: int
        """
        return self._sb_prop("last_seen_at")

    @property
    def online(self):
        """
        :returns: is this user online?
        :rtype: bool
        """
        return self._sb_prop("online")

    @property
    def chat(self):
        return self.__chat

class Message(SendbirdMixin):
    """
    Sendbird message object.
    Created when a message is recieved.

    :param data: message json, data after prefix in a sendbird websocket response
    :param client: client that the object belongs to

    :type data: dict
    :type client: Client
    """
    def __init__(self, id, channel_url, client, data = None):
        super().__init__(id, client, data = data)
        self.invoked = None

        self.__channel_url = None
        self.__chat = None
        self.__author = None
        self._url = f"{self.client.sendbird_api}/group_channels/{channel_url}/messages/{self.id}"

    def __repr__(self):
        return self.content if self.content else self.file_type

    def delete(self):
        """
        Delete a message sent by the client. This is exparamental, and may not work

        :returns: self
        :rtype: Message
        """
        if self.author != self.client.user:
            raise NotOwnContent("You cannot delete a message that does not belong to you")

        requests.delete(self._url)

        return self

    @property
    def author(self):
        """
        :returns: the author of this message
        :rtype: ChatUser
        """
        if not self.__author:
            self.__author = ChatUser(self._get_prop("user").get("guest_id"), self.client, self.chat)

        return self.__author

    @property
    def chat(self):
        """
        :returns: Chat that this message exists in
        :rtype: Chat
        """
        if not self.__chat:
            self.__chat = Chat(self.channel_url, self.client)

        return self.__chat

    @property
    def content(self):
        """
        :returns: String content of the message
        :rtype: str
        """
        return self._get_prop("message")

    @property
    def channel_url(self):
        """
        :returns: chat url for this messages chat
        :rtype: str
        """
        if not self.__channel_url:
            self.__channel_url = self._get_prop("channel_url")

        return self.__channel_url

    @property
    def send(self):
        """
        :returns: the send() method of this messages chat for easy replies
        :rtype: function
        """
        return self.chat.send_message

    @property
    def send_image_url(self):
        """
        :returns: the send_image_url() method of this messages chat for easy replies
        :rtype: function
        """
        return self.chat.send_image_url

    @property
    def type(self):
        """
        :returns: type of message. Text messages will return type MESG, while files return the file mime
        :rtype: str
        """
        return self._get_prop("type")

    @property
    def file_url(self):
        """
        :returns: message file url, if any
        :rtype: str, or None
        """
        if self.type == "MESG":
            return None

        return self._get_prop("file").get("url")

    @property
    def file_data(self):
        """
        :returns: file binary data, if any
        :rtype: str, or None
        """
        if self.type == "MESG":
            return None

        return requests.get(self.file_url, headers = self.client.sendbird_headers).content

    @property
    def file_type(self):
        """
        :returns: file type, if the message is a file
        :rtype: str, or None
        """
        if self.type == "MESG":
            return None

        return self._get_prop("file").get("type")

    @property
    def file_name(self):
        """
        :returns: file name, if the message is a file
        :rtype: str, or None
        """
        if self.type == "MESG":
            return None

        return self._get_prop("file").get("name")

class ChatInvite:
    """
    Chat update class.
    Created when an invite is recieved from the chat websocket.

    :param data: chat json, data after prefix in a sendbird websocket response
    :param client: client that the object belongs to

    :type data: dict
    :type client: Client
    """

    _status_codes = {
        10000: "accepted",
        10020: "invite",
        10022: "rejected"
    }

    def __init__(self, data, client):
        self.client = client
        self.debug = data
        self.__data = data

        self.__chat = None
        self.__channel_url = None
        self.__inviter = None
        self.__invitees = None
        self.__url = None

    def accept(self):
        """
        Accept an incoming invitation, if it is from a user.
        If it is not, the method will do nothing and return None.

        :returns: Chat that was joined, or None
        :rtype: Chat, or None
        """
        if not self.inviter or self.client.user not in self.invitees:
            return None

        data = json.dumps({
            "user_id": self.client.id
        })

        response = requests.put(f"{self.url}/accept", headers = self.client.sendbird_headers, data = data)

        if response.status_code != 200:
            raise BadAPIResponse(f"{response.url}, {response.text}")

        data = response.json()
        return self.chat

    def decline(self):
        """
        Decline an incoming invitation, if it is from a user.
        If it is not, the method will do nothing and return None.
        """
        if not self.inviter or self.client.user not in self.invitees:
            return None

        data = json.dumps({
            "user_id": self.client.id
        })

        response = requests.put(f"{self.url}/decline", headers = self.client.sendbird_headers, data = data)

    @property
    def url(self):
        """
        :returns: the request url to the incoming Chat
        :rtype: str
        """
        if not self.__url:
            self.__url = f"{self.client.sendbird_api}/group_channels/{self.channel_url}"

        return self.__url

    @property
    def channel_url(self):
        """
        :returns: the url to the incoming Chat
        :rtype: str
        """
        if not self.__channel_url:
            self.__channel_url = self.__data["channel_url"]

        return self.__channel_url

    @property
    def chat(self):
        """
        :returns: the incoming Chat
        :rtype: Chat
        """
        if not self.__chat:
            self.__chat = Chat(self.channel_url, self.client)

        return self.__chat

    @property
    def inviter(self):
        """
        :returns: if this update is an invite, returns the inviter
        :rtype: User, or None
        """
        if not self.__inviter:
            inviter = self.__data["data"]["inviter"]

            if not inviter:
                self.__inviter = None
                return self.__inviter

            self.__inviter = ChatUser(inviter["user_id"],self.client, self.chat, )

        return self.__inviter

    @property
    def invitees(self):
        """
        :returns: if this update is an invite, returns the invitees
        :rtype: list<User>, or None
        """
        if not self.__invitees:
            invitees = self.__data["data"]["invitees"]
            self.__invitees = [ChatUser(user["user_id"], self.client, self.chat) for user in invitees]

        return self.__invitees

    @property
    def type(self):
        """
        :returns: the type of the incoming chat data
        :rtype: str
        """
        return self._status_codes.get(self.__data["cat"], f"unknown: {self.__data['cat']}")
