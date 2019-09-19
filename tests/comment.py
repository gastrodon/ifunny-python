import unittest
import time
from ifunny import objects


def get_first(pool, content):
    for comment in pool:
        if comment.content == content:
            return comment

    return None


class CommentTest(unittest.TestCase):
    user = None
    comments = None

    @classmethod
    def setUpClass(cls):
        cls.user = objects.User.by_nick("kaffirtest")
        cls.comments = list(next(cls.user.timeline).comments)

    def test_root(self):
        comment = get_first(self.comments, "comment")

        assert next(comment.replies).root == comment

    def test_replies(self):
        comment = get_first(self.comments, "comment")

        for reply in comment.replies:
            assert reply.root == comment

    def test_depth(self):
        comment = get_first(self.comments, "comment")

        for reply in comment.replies:
            assert reply.depth >= 1

    def test_children(self):
        comment = get_first(self.comments, "comment")

        for child in comment.children:
            assert child.depth == 1

    def test_parent(self):
        comment = get_first(self.comments, "comment")

        assert next(comment.replies).parent == comment

    def test_reply_children(self):
        reply = next(get_first(self.comments, "comment").children)

        for child in reply.children:
            assert child.parent == reply

    def test_siblings(self):
        reply = next(get_first(self.comments, "comment").children)

        for sibling in reply.siblings:
            assert sibling.parent == get_first(self.comments, "comment")

    def test_content(self):
        assert get_first(self.comments, "comment").content == "comment"

    def test_post(self):
        assert isinstance(self.comments[0].post, objects.Post)

    def test_cid(self):
        assert self.comments[0].cid == self.comments[0].post.id

    def test_state(self):
        # should not be a top comment
        assert get_first(self.comments, "comment").state == "normal"

    def test_author(self):
        assert get_first(self.comments,
                         "comment").author == objects.User.by_nick("kaffir")

    def test_smile_count(self):
        assert self.comments[0].smile_count >= 0

    def test_unsmile_count(self):
        assert self.comments[0].unsmile_count >= 0

    def test_reply_count(self):
        assert get_first(self.comments, "comment").reply_count >= 8

    def test_is_root(self):
        assert self.comments[0].is_root == True

    def test_is_edited(self):
        assert get_first(self.comments, "Edit").content == "Edit"
        assert get_first(self.comments, "Edit").is_edited == True

    def test_attached_post(self):
        assert self.comments[-3].attached_post == self.comments[-3].post

    def test_mentioned_users(self):
        comment = get_first(self.comments, "kaffir")
        assert comment.mentioned_users[0] == objects.User.by_nick(
            comment.content)


if __name__ == '__main__':
    unittest.main()
