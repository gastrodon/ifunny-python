import unittest
import time, re
from ifunny import objects


class PostTest(unittest.TestCase):
    user = None
    pinned = None
    posts = {}

    @staticmethod
    def get_first_of(type, timeline):
        for post in timeline:
            if post.type == type:
                return post

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffirtest")
        cls.pinned = next(cls.user.timeline)
        for i in [
                "pic", "mem", "comics", "caption", "gif_caption", "video_clip",
                "gif"
        ]:
            cls.posts[i] = cls.get_first_of(i, cls.user.timeline)

    def test_smiles(self):
        user = next(self.pinned.smiles)
        assert isinstance(user, objects.User)

    def test_comments(self):
        comment = next(self.pinned.comments)
        assert isinstance(comment, objects.Comment)

    def test_smile_count(self):
        for post in self.posts.values():
            assert isinstance(post.smile_count, int)

        assert self.pinned.smile_count >= 1

    def test_unsmile_count(self):
        for post in self.posts.values():
            assert isinstance(post.unsmile_count, int)

    def test_guest_smile_count(self):
        for post in self.posts.values():
            assert isinstance(post.guest_smile_count, int)

    def test_comment_count(self):
        for post in self.posts.values():
            assert isinstance(post.comment_count, int)

        assert self.pinned.comment_count >= 1

    def test_view_count(self):
        for post in self.posts.values():
            assert isinstance(post.view_count, int)

        assert self.pinned.view_count >= 1

    def test_republication_count(self):
        for post in self.posts.values():
            assert isinstance(post.republication_count, int)

        assert self.pinned.republication_count >= 0

    def test_share_count(self):
        for post in self.posts.values():
            assert isinstance(post.share_count, int)

    def test_author(self):
        for post in self.posts.values():
            assert isinstance(post.author, objects.User)

        assert self.pinned.author == self.user

    def test_is_original(self):
        post = next(objects._mixin.ClientBase().collective)
        assert post.is_original == True

    def test_source(self):
        user = objects.User.by_nick("kaffirtest")
        post = None

        for _post in user.timeline:
            if not _post.is_original:
                post = _post
                break

        assert post.author != post.source.author

    def test_is_featured(self):
        feature = next(objects._mixin.ClientBase(paginated_size = 1).featured)
        assert feature.is_featured
        assert isinstance(feature.is_featured, bool)

    def test_is_pinned(self):
        assert self.pinned.is_pinned
        assert isinstance(self.pinned.is_pinned, bool)

    def test_is_abused(self):
        for post in self.posts.values():
            assert isinstance(post.is_abused, bool)
            assert not post.is_abused

    def test_type(self):
        for type in self.posts.keys():
            assert self.posts[type].type == type
            assert isinstance(self.posts[type].type, str)

    def test_tags(self):
        assert self.pinned.tags == ["tag"]
        assert isinstance(self.pinned.tags, list)
        assert isinstance(self.pinned.tags[0], str)

    def test_visibility(self):
        for post in self.posts.values():
            assert post.visibility == "public"

    def test_state(self):
        for post in self.posts.values():
            assert post.state == "published"

    def test_boostable(self):
        for post in self.posts.values():
            assert isinstance(post.boostable, bool)

    def test_created_at(self):
        for post in self.posts.values():
            assert isinstance(post.created_at, int)
            assert post.created_at < time.time()

    # published_at seems not to work
    def test_published_at(self):
        for post in self.posts.values():
            assert post.published_at is None

    def test_content_url(self):
        for post in self.posts.values():
            assert re.compile(
                "http(s)*://img.ifunny.co/((images)|(videos))/[a-f0-9_]+"
            ).match(post.content_url)

    def test_content(self):
        for post in self.posts.values():
            assert isinstance(post.content, bytes)

    def test_caption(self):
        for type in ["caption", "gif_caption"]:
            assert isinstance(self.posts[type].caption, str)

    def test_meta(self):
        for post in self.posts.values():
            assert post._meta != {}


if __name__ == '__main__':
    unittest.main()
