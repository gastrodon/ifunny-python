import unittest
import time
from ifunny import objects


class CommentTest(unittest.TestCase):
    user = None
    comments = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffirtest")
        cls.comments = list(next(cls.user.timeline).comments)

    def test_root(self):
        comment = self.comments[-1]

        assert next(comment.replies).root == comment

    def test_replies(self):
        comment = self.comments[-1]

        for reply in comment.replies:
            assert reply.root == comment

    def test_depth(self):
        comment = self.comments[-1]

        for reply in comment.replies:
            assert reply.depth >= 1

    def test_children(self):
        comment = self.comments[-1]

        for child in comment.children:
            assert child.depth == 1

    def test_parent(self):
        comment = self.comments[-1]

        assert next(comment.replies).parent == comment

    def test_reply_children(self):
        reply = next(self.comments[-1].children)

        for child in reply.children:
            assert child.parent == reply

    def test_siblings(self):
        reply = next(self.comments[-1].children)

        for sibling in reply.siblings:
            assert sibling.parent == self.comments[-1]

    def test_content(self):
        assert self.comments[-1].content == "comment"

    def test_post(self):
        assert isinstance(self.comments[0].post, objects.Post)

    def test_cid(self):
        assert self.comments[0].cid == self.comments[0].post.id

    def test_state(self):
        # should not be a top comment
        assert self.comments[-1].state == "normal"

    def test_author(self):
        assert self.comments[-1].author == objects.User.by_nick("kaffirapi")

    def test_smile_count(self):
        assert self.comments[0].smile_count >= 0

    def test_unsmile_count(self):
        assert self.comments[0].unsmile_count >= 0

    def test_reply_count(self):
        assert self.comments[-1].reply_count >= 8

    def test_is_root(self):
        assert self.comments[0].is_root == True

    def test_is_edited(self):
        assert self.comments[-5].is_edited == True

    def test_attached_post(self):
        assert self.comments[-3].attached_post == self.comments[-3].post

    def test_mentioned_users(self):
        comment = self.comments[-2]
        assert comment.mentioned_users[0] == objects.User.by_nick(
            comment.content)
