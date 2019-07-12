import json, time, requests
from ifunny.util.methods import determine_mime
from ifunny.util.exceptions import ChatNotActive

from ifunny.objects._main_app import ObjectMixin

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
            self._update = False
            response = requests.get(self._url, headers = self.client.sendbird_headers)

            if response.status_code == 403:
                self._account_data_payload = {}
                return self._account_data_payload

            try:
                self._account_data_payload = response.json()
            except KeyError:
                raise Exception(response.text)

        return self._account_data_payload

class Channel(SendbirdMixin):
    """
    iFunny Channel object

    :param id: channel_url of the Channel. ``Channel.channel_url`` is aliased to this value, though ``id`` is more consistent with other mixin objects and how they update themselves.
    :param client: Client that the Channel belongs to
    :param data: A data payload for the Channel to pull from before requests
    :param paginated_size: number of items to get for each paginated request. If above the call type's maximum, that will be used instead

    :type id: str
    :type client: Client
    :type data: dict
    :type paginated_size: int
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_url = self.id
        self._url = f"{self.client.sendbird_api}/group_channels/{self.id}/"

    def join(self):
        """
        Join this channel

        :returns: did this client join successfuly?
        :rtype: bool
        """
        response = requests.put(f"{self.client.api}/chats/channels/{self.channel_url}/members", headers = self.client.headers)

        return True if response.status_code == 200 else False

    def send_message(self, message):
        """
        Send a text message to a channel

        :param message: text that you will send

        :type message: str

        :raises: ChatNotActive if the attached client has not started the chat socket
        """
        if not self.client.socket.active:
            raise ChatNotActive("The chat socket has not been started")

        message_data = {
            "channel_url"   : self.channel_url,
            "message"       : message
        }

        self.client.socket.send(f"MESG{json.dumps(message_data, separators = (',', ':'))}\n")

    def send_image_url(self, image_url, width = 780, height = 780):
        """
        Send an image to a channel from a url source.

        :param image_url: url where the image is located. This should point to the image itself, not a webpage with an image
        :param width: width of the image in pixels
        :param height: heigh of the image in pixels

        :type image_url: str
        :type width: int
        :type height: int

        :raises: ChatNotActive if the attached client has not started the chat socket
        """
        if not self.client.socket.active:
            raise ChatNotActive("The chat socket has not been started")

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
                    "real_height"   : int(780 if type == "tall" else 780 * lower_ratio),
                    "real_width"    : int(780 if type == "wide" else 780 * lower_ratio),
                    "height"        : width,
                    "width"         : height,
                }
            ]
        }

        self.client.socket.send(f"FILE{json.dumps(response_data, separators = (',', ':'))}\n")

    @property
    def send(self):
        """
        :returns: this classes send_message method
        :rtype: function
        """
        return self.send_message

class Message:
    """
    Sendbird message object.
    Created when a message is recieved.

    :param data: message json, data after prefix in a sendbird websocket response
    :param client: client that the object belongs to

    :type data: dict
    :type client: Client
    """
    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.__message = None
        self.__channel_url = None
        self.__channel = None

    def __repr__(self):
        return self.content

    @property
    def channel(self):
        """
        :returns: Channel that this message exists in
        :rtype: Channel
        """
        if not self.__channel:
            self.__channel = Channel(self.channel_url, self.client)

        return self.__channel

    @property
    def content(self):
        """
        :returns: String content of the message
        :rtype: str
        """
        if not self.__message:
            self.__message = self.__data["message"]

        return self.__message

    @property
    def channel_url(self):
        """
        :returns: channel url for this messages channel
        :rtype: str
        """
        if not self.__channel_url:
            self.__channel_url = self.__data["channel_url"]

        return self.__channel_url

    @property
    def send(self):
        """
        :returns: the send() method of this messages channel for easy replies
        :rtype: function
        """
        return self.channel.send_message

    @property
    def send_image_url(self):
        """
        :retunrs: the send_image_url() method of this messages channel for easy replies
        :rtype: function
        """
        return self.channel.send_image_url

class IncomingChannel:
    """
    Incoming Channel class.
    Created when an imcomming Channel is recieved from the chat websocket.

    :param data: channel json, data after prefix in a sendbird websocket response
    :param client: client that the object belongs to

    :type data: dict
    :type client: Client
    """

    _status_codes = {
        10000: "accepted",
        10020: "new",
        10022: "rejected"
    }

    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.__channel = None
        self.__channel_url = None
        self.__inviter = None
        self.__invitees = None
        self.__url = None

    def accept(self):
        """
        Accept an incoming invitation, if it is from a user.
        If it is not, the method will do nothing and return None.

        :returns: Channel that was joined, or None
        :rtype: Channel, or None
        """
        if not self.inviter:
            return None

        headers = self.client.sendbird_headers

        data = json.dumps({
            "user_id": self.client.id
        })

        response = requests.put(f"{self.url}/accept", headers = headers, data = data)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()
        return self.channel

    def decline(self):
        """
        Decline an incoming invitation, if it is from a user.
        If it is not, the method will do nothing and return None.
        """
        if not self.inviter:
            return None

        headers = self.client.sendbird_headers

        data = json.dumps({
            "user_id": self.client.id
        })

        response = requests.put(f"{self.url}/decline", headers = headers, data = data)

    @property
    def url(self):
        """
        :retunrs: the request url to the incoming Channel
        :rtype: str
        """
        if not self.__url:
            self.__url = f"{self.client.sendbird_api}/group_channels/{self.channel_url}"

        return self.__url

    @property
    def channel_url(self):
        """
        :retunrs: the url to the incoming Channel
        :rtype: str
        """
        if not self.__channel_url:
            self.__channel_url = self.__data["channel_url"]

        return self.__channel_url

    @property
    def channel(self):
        """
        :retunrs: the incoming Channel
        :rtype: Channel
        """
        if not self.__channel:
            self.__channel = Channel(self.channel_url, self.client)

        return self.__channel

    @property
    def inviter(self):
        """
        :retunrs: the user who dispatched an invite to this group, or None
        :rtype: User, or None
        """
        if not self.__inviter:
            inviter = self.__data["data"]["inviter"]

            if not inviter:
                self.__inviter = None
                return self.__inviter

            self.__inviter = User(inviter["user_id"], self.client)

        return self.__inviter

    @property
    def invitees(self):
        """
        :returns: the users who were invited with this instance of an incoming Channel
        :rtype: list<User>, or None
        """
        if not self.__invitees:
            invitees = self.__data["data"]["invitees"]
            self.__invitees = [User(user["user_id"], self.client) for user in invitees]

        return self.__invitees

    @property
    def status(self):
        """
        :returns: the status of the incoming channel data
        :rtype: str
        """
        return self._status_codes.get(self.__data["cat"], f"unknown: {self.__data['cat']}")
