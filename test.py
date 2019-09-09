#! /usr/bin/env python3
import unittest
import sys

print(f"args: {sys.argv}")

if not "--auth-only" in sys.argv:
    from tests.user import UserTest
    from tests.client_base import ClientBaseTest
    from tests.post import PostTest
    from tests.comment import CommentTest
    from tests.channel import ChannelTest
    from tests.digest import DigestTest

if "--auth" in sys.argv or "--auth-only" in sys.argv:
    from tests.auth.client import ClientTest

for _ in range(len(sys.argv) - 1):
    sys.argv.pop()

unittest.main()
