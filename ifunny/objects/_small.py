import requests
from ifunny import objects
from ifunny.objects import _mixin as mixin


class Image:
    """
    Wrapper for image properties

    :param url: location of the image
    :param background: image background color
    :param client: client who requests the image

    :type url: str
    :type background: str
    :type client: Client
    """
    def __init__(self, url, background = None, client = mixin.ClientBase()):
        self.client = client
        self.url = url
        self.background = background

    @property
    def content(self):
        """
        :returns: image content
        :rtype: bytes
        """
        return requests.get(url, headers = client.headers)


class Rating:
    """
    iFunny profile ratings

    :param user: user who this rating is of
    :param client: client who requests the rating
    :param data: data payload of this rating

    :type user: User
    :type client: Client
    :type data: dict
    """
    def __init__(self, user, client = mixin.ClientBase(), data = None):
        self.user = user
        self._object_data_payload = data
        self._update = False

    def _get_prop(self, key, default = None):
        try:
            return self._object_data[key]

        except KeyError:
            return self.fresh._object_data.get(key, default)

    @property
    def _object_data(self):
        if not self._object_data_payload or self._update:
            self._object_data_payload = self.user.fresh._rating_data

        return self._object_data_payload

    @property
    def fresh(self):
        """
        :returns: this object with the update flag set
        :rtype: Rating
        """
        self._update = True
        return self

    @property
    def _current(self):
        return self._get_prop("current_level")

    @property
    def _next(self):
        return self._get_prop("next_level")

    @property
    def _max(self):
        return self._get_prop("max_level")

    @property
    def points(self):
        """
        :returns: the points of this user
        :rtype: int
        """
        return self._get_prop("points")

    @property
    def visible(self):
        """
        :returns: is the level of this user visible?
        :rtype: bool
        """
        return self._get_prop("is_show_level")

    @property
    def level(self):
        """
        :returns: the level of this user
        :rtype: int
        """
        return self._current.get("value")

    @property
    def level_points(self):
        """
        :returns: the points required for the level of this user
        :rtype: int
        """
        return self._current.get("points")

    @property
    def next(self):
        """
        :returns: the next level of this user
        :rtype: int
        """
        return self._next.get("value")

    @property
    def next_points(self):
        """
        :returns: the points required for the next level of this user
        :rtype: int
        """
        return self._next.get("points")

    @property
    def max(self):
        """
        :returns: the max level of this user
        :rtype: int
        """
        return self._max.get("value")

    @property
    def max_points(self):
        """
        :returns: the points required for the max level of this user
        :rtype: int
        """
        return self._max.get("points")


class Ban(mixin.ObjectMixin):
    """
    iFunny ban
    subclass of ObjectMixin
    """
    def __init__(self, *args, user = None, **kwargs):
        if not user:
            raise ValueError("user is required")

        super().__init__(*args, **kwargs)
        self.user = user

        if self._object_data_payload:
            self._object_data_payload = {"ban": self._object_data_payload}

        key = self.user.id if self.user.id else "my"
        self._url = f"{self.api}/users/{key}/bans/{self.id}"

    def _get_prop(self, key, default = None):
        if not self._object_data["ban"].get(key, None):
            self._update = True

        return self._object_data["ban"].get(key, default)

    @property
    def reason(self):
        """
        :returns: reason for this ban
        :rtype: str
        """
        return self._get_prop("ban_reason")

    @property
    def created_at(self):
        """
        :returns: timestamp of when this ban was created
        :rtype: int
        """
        return self._get_prop("created_at")

    @property
    def expires_at(self):
        """
        :returns: timestamp of when this ban expires
        :rtype: int
        """
        return self._get_prop("date_until")

    @property
    def type(self):
        """
        :returns: type of ban
        :rtype: str
        """
        return self._get_prop("type")

    @property
    def index(self):
        """
        :returns: ban index relative to other bans (starting at 1)
        :rtype: int
        """
        return self._get_prop("pid")

    @property
    def is_appealed(self):
        """
        :returns: has this ban been appealed?
        :rtype: bool
        """
        return self._get_prop("is_appealed")

    @property
    def is_appealable(self):
        """
        :returns: can this ban be appealed?
        :rtype: bool
        """
        return self._get_prop("can_be_appealed")

    @property
    def was_shown(self):
        """
        :returns: was the client notified of this ban?
        :rtype: bool
        """
        return self._get_prop("was_shown")

    @property
    def is_active(self):
        """
        :returns: is this ban active?
        :rtype: bool
        """
        return self._get_prop("is_active")

    @property
    def is_shortable(self):
        """
        :returns: can this ban be shortened?
        :rtype: bool
        """
        return self._get_prop("is_shortable")


class Achievement(mixin.ObjectMixin):
    """
    iFunny achievements
    subclass of ObjectMixin
    """
    def __init__(self, *args, user = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        key = self.user.id if self.user else "my"
        self._url = f"{self.api}/users/{key}/achievements/{self.id}"

    def _get_prop(self, key, default = None):
        if not self._object_data.get(key, None):
            self._update = True

        return self._object_data.get(key, default)

    def _task_data(self, id):
        for task in self._get_prop("tasks"):
            if task.get("id") == id:
                return task

        return {}

    @property
    def _type(self):
        return self._get_prop("type_achievement", {})

    @property
    def _season_data(self):
        return self._type.get("season")

    @property
    def tasks(self):
        """
        :returns: tasks to complete this achievement
        :rtype: list<Task>
        """
        return [
            Task(item["id"], self, data = item)
            for item in self._get_prop("tasks")
        ]

    @property
    def season(self):
        """
        :returns: this achievements season
        :rtype: Season
        """
        return Season(self, data = self._season_data)

    @property
    def start_at(self):
        """
        :returns: achievement start timestamp
        :rtype: int
        """
        return self._get_prop("period_start_at")

    @property
    def expire_at(self):
        """
        :returns: achievement expiration timestamp
        :rtype: int
        """
        return self._get_prop("period_stop_at")

    @property
    def was_shown(self):
        """
        :returns: was this achievement shown?
        :rtype: bool
        """
        return self._get_prop("was_shown")

    @property
    def title(self):
        """
        :returns: this achievements title
        :rtype: str
        """
        return self._type.get("title")

    @property
    def description(self):
        """
        :returns: this achievements description
        :rtype: str
        """
        return self._type.get("description")

    @property
    def action_text(self):
        """
        :returns: this achievements action_text
        :rtype: str
        """
        return self._type.get("action_text")

    @property
    def period(self):
        """
        :returns: this achievements period
        :rtype: str
        """
        return self._type.get("period")

    @property
    def status(self):
        """
        :returns: this achievements status
        :rtype: str
        """
        return self._type.get("status")

    @property
    def reward(self):
        """
        :returns: this achievements reward
        :rtype: int
        """
        return self._type.get("reward_points")

    @property
    def complete_text(self):
        """
        :returns: this achievements text when complete
        :rtype: str
        """
        return self._type.get("complete_text")

    @property
    def complete_description(self):
        """
        :returns: this achievements description when complete
        :rtype: str
        """
        return self._type.get("complete_description")


class Task:
    """
    Achievement task

    :param id: id of this task
    :param achievement: achievement that this task is for
    :param data: data payload of this task

    :type id: str
    :type achievement: Achievement
    :type data: dict
    """
    def __init__(self, id, achievement, data = None):
        self.achievement = achievement
        self._object_data_payload = data
        self.id = id
        self._update = False

    def _get_prop(self, key, default = None):
        try:
            return self._object_data[key]
        except KeyError:
            return self.fresh.get(key, data)

    @property
    def _object_data(self):
        if self._update or not self._object_data_payload:
            self._object_data_payload = self.achievement._task_data(self.id)

        return self._object_data_payload

    @property
    def _type(self):
        return self._get_prop("type_task", {})

    @property
    def fresh(self):
        """
        :returns: this object with the update flag set
        :rtype: Task
        """
        self._update = True
        return self

    @property
    def count(self):
        """
        :returns: times to complete task required
        :rtype: int
        """
        return self._get_prop("count")

    @property
    def event(self):
        """
        :returns: task event
        :rtype: str
        """
        return self._type.get("event")


class Season:
    """
    Achievement season

    :param achievement: achievement that this season is for
    :param data: data payload of this task

    :type achievement: Achievement
    :type data: dict
    """
    def __init__(self, achievement, data = None):
        self.achievement = achievement
        self._object_data_payload = data

    def _get_prop(self, key, default = None):
        try:
            return self._object_data[key]

        except KeyError:
            return self.fresh.get(key, default)

    @property
    def _object_data(self):
        if not self._object_data_payload or self._update:
            self._object_data_payload = self.achievement._season_data

        return self._object_data_payload

    @property
    def id(self):
        """
        :returns: the id of this season
        :rtype: str
        """
        return self._get_prop("id")

    @property
    def title(self):
        """
        :returns: the title of this season
        :rtype: str
        """
        return self._get_prop("title")

    @property
    def description(self):
        """
        :returns: the description of this season
        :rtype: str
        """
        return self._get_prop("description")

    @property
    def status(self):
        """
        :returns: the status of this season
        :rtype: str
        """
        return self._get_prop("status")

    @property
    def start_at(self):
        """
        :returns: the start_at timestamp
        :rtype: int
        """
        return self._get_prop("start_at")

    @property
    def expire_at(self):
        """
        :returns: the expire_at timestamp
        :rtype: int
        """
        return self._get_prop("stop_at")
