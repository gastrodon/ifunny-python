# What's new

### 0.9.2
- `ClientBase` now has `User-Agent` headers. I don't know why it didn't before
- `Client.channels` was broken because of weird data, fixed it
- `Client.digests` was broken because of weird nested data, fixed it
- some typos fixed in the docs
- some incorrect \_get\_prop calls fixed for some properties
- non-chat things are (mostly) tested

### 0.9.1
- fix a bug with importing util
- fix a bug with client using deprecated variable `sendbird_session_key` instead of the property `messenger_token`

### 0.9.0
- split read-only methods out of `Client` to `ClientBase` for things that should not need logging in
- moved around a bunch of imports and started import modules instead of the classes in them. Fixes some circular dependency problems that may arise

### 0.8.0
- A bunch of setters for properties in `Post` and `User`
- `client.post_image[_url]` can now have scheduled posts
- `client.search_users`, `client.search_chats`, `client.search_tags` and `client.suggested_tags` for searching
- fixed bugs caused by sendbird vs ifunny api inconsistencies
- reply comments can now return replies
- `Comment.parent`, `Comment.children` and `Comment.siblings` generators for comments attached to others. These are not very fast
- Fix a bug getting certain properties that are sourced from `foo._get_prop("num")` from partial payloads raising a KeyError
- Add a check for deleted objects in `ObjectMixin` and made behavior more consistent

### 0.7.0
- generator for `client.digests` for iterating through available digests
- `objects.Digest` object, representing explore digests
- `Client.channels` property, returning featured channels from explore
- Basic auth is now a fallback, so read only things can be done without logging in
- Messed with the style in `versioninfo.md` (that's this!)
- `Channel` has been renamed to `chat` for better api consistency
- references to `channel` and `channel` are being changed to `chat` and `Chat`, respectively. This may be buggy and missing some instances at first.
- Messages now include file messages having `file_url`, `file_data`, `file_name`, and `file_type` properties
- Messages listener now enscopes file messages
- fixed incorrect docs in message type property

### 0.6.0
- `client.trending_channels` property, for trending channels in explore
- generators for `client.home`, `client.featured`, `client.collective` feeds
- `client.reads` generator for viewed posts
- user `pic_url` property
- chat `name` property
- chat `add_operator` and `remove_operator` methods
- chat `leave` method, so you can escape

### 0.5.2
- Fix bug getting `User.chat_channel`
- Fix bug in `Message.author`
- Don't read messages by default when sending
- Disable req_id. It is bugged

### 0.5.1
- started keeping track of new features
- use of `client.next_req_id` for messages (still won't work for pics), which had been implemented much earlier
- being able to mark messages as read
- fix a bug in `ChatInvite.accept` and `ChatInvite.decline` methods
- fix a typo in docs (py 3.7, not 2.7)
- `Chat.public` and `Chat.private` properties
- Chats can now `kick()` users, and ChatUser can now be `kick()`
- Chats can now `invite()` users
- Chats can now be frozen, either by setting `Chat.frozen = [True | False]` or by using `Chat.freeze`/`Chat.freeze` with auto unfreeze/freeze

### 0.5 (from memory)
- Chats can now be `read()`
- Chats have message iterators
- Chats now have member iterators
- Chats now can report on admins and operators
- Chats have a bunch of new properties
- Chats can now have data fetched lazily, and no longer require a data payload
- Messages now report on file type
- Messages can now be deleted with `delete()` (exparamental)
- Messages can now have data fetched lazily, and no longer require a data payload
- Messages have a bunch of new properties
- ChatUser now exists, for representing users relative to a Chat (exparamental)
