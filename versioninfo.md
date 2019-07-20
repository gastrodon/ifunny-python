### What's new

#### 0.5.2
- Fix bug getting `User.chat_channel`
- Fix bug in `Message.author`
- Don't read messages by default when sending
- Disable req_id. It is bugged

#### 0.5.1
- started keeping track of new features
- use of `client.next_req_id` for messages (still won't work for pics), which had been implemented much earlier
- being able to mark messages as read
- fix a bug in `ChannelInvite.accept` and `ChannelInvite.decline` methods
- fix a typo in docs (py 3.7, not 2.7)
- `Channel.public` and `Channel.private` properties
- Channels can now `kick()` users, and ChannelUser can now be `kick()`
- Channels can now `invite()` users
- Channels can now be frozen, either by setting `Channel.frozen = [True | False]` or by using `Channel.freeze`/`Channel.freeze` with auto unfreeze/freeze

#### 0.5 (from memory)
- Channels can now be `read()`
- Channels have message iterators
- Channels now have member iterators
- Channels now can report on admins and operators
- Channels have a bunch of new properties
- Channels can now have data fetched lazily, and no longer require a data payload
- Messages now report on file type
- Messages can now be deleted with `delete()` (exparamental)
- Messages can now have data fetched lazily, and no longer require a data payload
- Messages have a bunch of new properties
- ChannelUser now exists, for representing users relative to a Channel (exparamental)
