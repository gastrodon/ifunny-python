import unittest, json, os, requests, re, time
from ifunny import Client, objects


class ClientTest(unittest.TestCase):
    client = None
    ts = None
    image_png = "https://safebooru.org//images/2782/308d1f35ff658731d3ade7f5b49673a85f5a6dc9.png"
    image_jpg = "https://safebooru.org//samples/2795/sample_6af4d9d8e79f9012a95b943626abd893ad306431.jpg"
    image_gif = "https://safebooru.org//images/2760/d2291266b9fabf3d6d5e822322b70eb2.gif"

    @classmethod
    def setUpClass(cls):
        cls.ts = int(time.time())
        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username, password = config["username"], config["password"]

        cls.client = Client().login(username, password)

    def test_bearer_token(self):
        regex = "[a-f0-9]{64}"
        assert re.search(
            regex,
            self.client._Client__token).group() == self.client._Client__token

    def test_messenger_token(self):
        regex = "[a-f0-9]{40}"
        assert re.search(
            regex,
            self.client.messenger_token).group() == self.client.messenger_token

    def test_messenger_token_setter(self):
        new = "foobar"
        self.client.messenger_token = new
        assert self.client.messenger_token == new
        self.client.messenger_token == None

    def test_headers(self):
        headers = {
            "Authorization": f"Bearer {self.client._Client__token}",
            "User-Agent": self.client._user_agent
        }

        assert self.client.headers == headers

    def test_sendbird_headers(self):
        headers = {
            "User-Agent": "jand/3.096",
            "Session-Key": self.client.messenger_token
        }

        assert self.client.sendbird_headers == headers

    def test_next_req_id(self):
        req = self.client.next_req_id
        assert self.client.next_req_id == req + 1
        assert req > self.ts

    def test_user(self):
        assert self.client.user == objects.User.by_nick("kaffirtest")

    def test_email(self):
        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username = config["username"]

        assert self.client.email == username

    def test_id(self):
        regex = "[a-f0-9]{24}"
        assert re.search(regex, self.client.id)

    def test_timeline(self):
        assert next(self.client.timeline).author == self.client.user

    def test_reads_paginated(self):
        reads = self.client._reads_paginated()
        for read in reads["items"]:
            assert isinstance(read, objects.Post)

    def test_reads(self):
        reads = self.client.reads
        assert isinstance(next(reads), objects.Post)

    def test_home_paginated(self):
        home = self.client._home_paginated()
        for post in home["items"]:
            assert isinstance(post, objects.Post)

    def test_home(self):
        home = self.client.home
        assert next(home).author == objects.User.by_nick("kaffir")

    def test_smiles_paginated(self):
        smiles = self.client._smiles_paginated()
        for smile in smiles["items"]:
            assert isinstance(smile, objects.Post)

    def test_smiles(self):
        smiles = self.client.smiles
        assert isinstance(next(smiles), objects.Post)

    def test_smile_on_self(self):
        smile = next(self.client.smiles)
        assert smile.author == self.client.user

    def test_comments_paginated(self):
        comments = self.client._comments_paginated()
        for comment in comments["items"]:
            assert isinstance(comment, objects.Comment)

    def test_comments(self):
        comments = self.client.comments
        next(comments).author == self.client.user

    def test_login(self):
        client = Client()

        with open(
                f"{os.path.dirname(os.path.realpath(__file__))}/test_auth.json"
        ) as stream:
            config = json.load(stream)
            username, password = config["username"], config["password"]

        client.login(username, password)

        assert client.user == objects.User.by_nick("kaffirtest")

    def test_post_image_png(self):
        image = requests.get(self.image_png).content
        post = self.client.post_image(image, wait = True)
        timeline = self.client.user.timeline

        next(timeline)

        try:
            assert post == next(timeline)
            assert post.type == "pic"
        finally:
            post.delete()

    def test_post_image_jpg(self):
        image = requests.get(self.image_jpg).content
        post = self.client.post_image(image, wait = True)
        timeline = self.client.user.timeline

        next(timeline)

        try:
            assert post == next(timeline)
            assert post.type == "pic"
        finally:
            post.delete()

    def test_post_gif(self):
        image = requests.get(self.image_gif).content
        post = self.client.post_image(image, wait = True, type = "gif")
        timeline = self.client.user.timeline

        next(timeline)

        try:
            assert post == next(timeline)
            assert post.type == "gif"
        finally:
            post.delete()

    def test_post_image_png_url(self):
        post = self.client.post_image_url(self.image_png, wait = True)
        timeline = self.client.user.timeline

        next(timeline)

        try:
            assert post == next(timeline)
            assert post.type == "pic"
        finally:
            post.delete()

    def test_post_image_jpg_url(self):
        post = self.client.post_image_url(self.image_jpg, wait = True)
        timeline = self.client.user.timeline

        next(timeline)

        try:
            assert post == next(timeline)
            assert post.type == "pic"
        finally:
            post.delete()

    def test_post_image_gif_url(self):
        post = self.client.post_image_url(self.image_gif,
                                          wait = True,
                                          type = "gif")
        timeline = self.client.user.timeline

        next(timeline)

        try:
            assert post == next(timeline)
            assert post.type == "gif"
        finally:
            post.delete()


if __name__ == '__main__':
    unittest.main()
