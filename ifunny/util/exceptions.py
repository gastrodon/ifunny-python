class ChatNotActive(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ChatAlreadyActive(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AlreadyAuthenticated(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NotAuthenticated(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TooManyMentions(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NoContent(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NotOwnContent(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class OwnContent(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BadAPIResponse(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FailedToComment(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MemberNotInChat(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Forbidden(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Unavailable(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RateLimit(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CaptchaFailed(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
