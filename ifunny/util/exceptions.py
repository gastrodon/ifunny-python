class ChatNotActive(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ChatAlreadyActive(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class NoContent(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class TooManyMentions(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class NotOwnPost(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class BadAPIResponse(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class BadAPIResponse(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class FailedToComment(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class AlreadyAuthenticated(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
