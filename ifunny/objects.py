import json, time, random, requests
from ifunny.utils import determine_mime, invalid_type

class ObjectBase:
    def __init__(self, id, client, data = None, update_interval = 30):
        self.client = client
        self.id = id

        self._account_data_payload = data
        self._updated = time.time()
        self._update_interval = update_interval

        self._url = None

    def _get_prop(self, key):
        if not self._account_data.get(key, None):
            self._updated = 0

        return self._account_data[key]

    def _update(self):
        self._account_data_payload = None

    def _paginated_data(self, data, items):
        paging = paging = {
            "prev":     data["paging"]["cursors"]["prev"] if data["paging"]["hasPrev"] else None,
            "next":     data["paging"]["cursors"]["next"] if data["paging"]["hasNext"] else None
        }

        return {
            "items":    items,
            "paging":   paging
        }

    @property
    def _account_data(self):
        if time.time() - self._updated > self._update_interval or self._account_data_payload is None:
            self._updated = time.time()
            self._account_data_payload = requests.get(self._url, headers = self.client.headers).json()["data"]

        return self._account_data_payload

class User(ObjectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = f"{self.client.api}/users/{self.id}"

    def __repr__(self):
        return self.nick

    # public methods

    def timeline(self, limit = 25, prev = None, next = None):
        params = {
            "limit":    limit
        }

        if next:
            params["next"] = next
        elif prev:
            params["prev"] = prev

        response = requests.get(f"{self.client.api}/timelines/users/{self.id}", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()["data"]["content"]

        items = [Post(item["id"], self.client) for item in data["items"]]

        return self._paginated_data(data, items)

    def subscribers(self, limit = 25, prev = None, next = None):
        params = {
            "limit":    limit
        }

        if next:
            params["next"] = next
        elif prev:
            params["prev"] = prev

        response = requests.get(f"{self._url}/subscribers", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()["data"]["users"]


        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return self._paginated_data(data, items)

    def subscriptions(self, limit = 25, prev = None, next = None):
        params = {
            "limit":    limit
        }

        if next:
            params["next"] = next
        elif prev:
            params["prev"] = prev

        response = requests.get(f"{self._url}/subscriptions", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()["data"]["users"]

        items = [User(item["id"], self.client, data = item) for item in data["items"]]

        return self._paginated_data(data, items)

    def subscribe(self):
        response = requests.put(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    def unsubscribe(self):
        response = requests.delete(f"{self._url}/subscribers", headers = self.client.headers)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    def block(self, type = "user"):
        valid = ["user", "installation"]

        if type not in valid:
            raise invalid_type("type", type, valid)
            
        params = {
            "type": type
        }

        response = requests.put(f"{self.client.api}/users/my/blocked/{self.id}", params = params, headers = self.client.headers)

        if response.status_code != 200:
            if response.json().get("error") == "already_blocked":
                return False

            raise Exception(response.text)

        return True

    def unblock(self):
        params = {
            "type": "user"
        }

        response = requests.delete(f"{self.client.api}/users/my/blocked/{self.id}", params = params, headers = self.client.headers)

        if response.status_code != 200:
            if response.json().get("error") == "not_blocked":
                return False

            raise Exception(response.text)

        return True

    def report(self, type):
        valid = ["hate", "nude", "spam", "target", "harm"]

        if type not in valid:
            raise invalid_type("type", type, valid)

        params = {
            "type": type
        }

        response = requests.put(f"{self._url}/abuses", headers = self.client.headers, params = params)

        if response.status_code != 200:
            raise Exception(response.text)

        return True

    # public properties

    # authentication independant attributes

    @property
    def nick(self):
        return self._get_prop("nick")

    @property
    def about(self):
        return self._get_prop("about")

    @property
    def posts(self):
        return self._get_prop("num")["featured"]

    @property
    def featured(self):
        return self._get_prop("num")["featured"]

    @property
    def smiles(self):
        return self._get_prop("num")["total_smiles"]

    @property
    def subscriber_count(self):
        return self._get_prop("num")["subscribers"]

    @property
    def subscription_count(self):
        return self._get_prop("num")["subscriptions"]

    @property
    def is_verified(self):
        return self._get_prop("is_verified")

    @property
    def is_banned(self):
        return self._get_prop("is_banned")

    @property
    def is_deleted(self):
        return self._get_prop("is_deleted")

    @property
    def days(self):
        return self._get_prop("meme_experience")["days"]

    @property
    def rank(self):
        return self._get_prop("meme_experience")["rank"]

    @property
    def nick_color(self):
        try:
            return self._get_prop("nick_color")
        except KeyError:
            return None

    @property
    def chat_privacy(self):
        return self._get_prop("messaging_privacy_status")

    # authentication dependant attributes

    @property
    def blocked(self):
        return self._get_prop("is_blocked")

    @property
    def blocking_me(self):
        return self._get_prop("are_you_blocked")

    @property
    def can_chat(self):
        return self._get_prop("is_available_for_chat")

    @property
    def notification_updates(self):
        return self._get_prop("is_subscribed_to_updates")

    @property
    def is_subscribed(self):
        return self._get_prop("is_in_subscribers")

    @property
    def is_subscription(self):
        return self._get_prop("is_in_subscriptions")


class Post(ObjectBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class Comment:
    def __init__(self, data, client):
        self.client = client
        self.__data = data
        self.__creator = None
        # v4/users/data["id"] links to the user data

        self.text = data["text"]
        self.id = data["id"]
        self.cid = data["cid"]
        self.state = data["state"] #top comments have the state top, others have normal
        self.is_reply = data["is_reply"]
        self.smiles = data["num"].get("smiles", 0)
        self.unsmiles = data["num"].get("unsmiles", 0)

    def __repr__(self):
        return self.text

class ChatChannel:
    def __init__(self, data, client):
        self.client = client
        self.__data = data

        self.sendbird_url = data["channel_url"]
        self.id = data["channel_id"]
        self.type = data["channel_type"]

class MessageContext:
    def __init__(self, client, data):
        self.client = client
        self.socket = self.client.socket
        self.commands = self.client.commands
        self.channel_url = data["channel_url"]
        self.message = data["message"]

    def send(self, message):
        response_data = {
            "channel_url"   : self.channel_url,
            "message"       : message
        }

        return self.socket.send(f"MESG{json.dumps(response_data, separators = (',', ':'))}\n")


    def send_file_url(self, image_url, width = 780, height = 780):
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
                    "real_height"   : int(780 if type is "tall" else 780 * lower_ratio),
                    "real_width"    : int(780 if type is "wide" else 780 * lower_ratio),
                    "height"        : width,
                    "width"         : height,
                }
            ]
        }

        return self.socket.send(f"FILE{json.dumps(response_data, separators = (',', ':'))}\n")

    @property
    def prefix(self):
        return self.client.prefix
