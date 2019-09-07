import unittest
from ifunny import objects


class DigestTest(unittest.TestCase):
    user = None
    digest = None

    # stop when we find an error
    def run(self, result = None):
        if not result.errors:
            super(DigestTest, self).run(result)

    @classmethod
    def setUpClass(cls):
        cls.user = objects._mixin.ClientBase()
        cls.digest = next(cls.user.digests)

    def test_digest(self):
        assert isinstance(next(self.user.digests), objects.Digest)

    def test_unread_count(self):
        assert self.digest.unread_count >= 0

    def test_read(cls):
        assert isinstance(cls.digest.read(), objects.Digest)
        assert cls.digest.unread_count == 0

    def test_feed(self):
        assert isinstance(next(self.digest.feed), objects.Post)

    def test_title(self):
        assert isinstance(self.digest.title, str)

    def test_smile_count(self):
        assert self.digest.smile_count > 0

    def test_total_smiles_alias(self):
        assert self.digest.total_smiles == self.digest.smile_count

    def test_comment_count(self):
        assert self.digest.comment_count >= 0

    def test_count(self):
        assert self.digest.count > 0

    def test_index_alias(self):
        assert self.digest.index == self.digest.index
