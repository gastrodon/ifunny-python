import requests

from ifunny.util import exceptions

mime_types = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "jpe": "image/jpeg",
    "bmp": "image/bmp",
    "midi": "audio/midi",
    "mpeg": "video/mpeg",
    "oog": "video/oog",
    "webm": "video/webm",
    "wav": "audio/wav"
}


def request(method, url, codes = {200}, errors = {}, **kwargs):
    response = requests.request(method.lower(), url, **kwargs)

    if response.status_code in codes:
        return response.json()

    if response.status_code in errors.keys():
        err = errors[response.status_code]
        raise err["raisable"](err.get("message", ""))

    if response.status_code == 404:
        raise exceptions.NotFound(response.text)

    if response.status_code == 403:
        if response.json()["error"].startswith("already_"):
            raise exceptions.RepeatedAction(response.text)

        if response.json()["error"] == "you_are_blocked":
            raise exceptions.Blocked(response.text)

        raise exceptions.Forbidden(response.text)

    if response.status_code == 429:
        raise exceptions.RateLimit(response.text)

    raise exceptions.BadAPIResponse(f"{url}, {response.text}")


def determine_mime(url, bias = "image/png"):
    global mime_types
    return mime_types.get(url.split(".")[-1], bias)


def paginated_format(data, items):
    paging = {
        "prev":
        data["paging"]["cursors"]["prev"]
        if data["paging"]["hasPrev"] else None,
        "next":
        data["paging"]["cursors"]["next"]
        if data["paging"]["hasNext"] else None
    }

    return {"items": items, "paging": paging}


def paginated_params(limit, prev, next, ex_params = {}):
    params = {"limit": limit}

    if next:
        params["next"] = next
    elif prev:
        params["prev"] = prev

    return {**params, **ex_params}


def paginated_data(source_url,
                   data_key,
                   headers,
                   limit = 25,
                   prev = None,
                   next = None,
                   post = False,
                   ex_params = {}):
    params = paginated_params(limit, prev, next, ex_params)

    if post:
        response = requests.post(source_url, headers = headers, data = params)
    else:
        response = requests.get(source_url, headers = headers, params = params)

    if response.status_code != 200:
        raise exceptions.BadAPIResponse(
            f"requesting {response.url} failed\n{response.text}")

    if data_key:
        return response.json()["data"][data_key]

    return response.json()["data"]


def paginated_generator(source, *args):
    buffer = source(*args)

    while True:
        for item in buffer["items"]:
            yield item

        if not buffer["paging"]["next"]:
            break

        buffer = source(*args, next = buffer["paging"]["next"])


def get_slice(source, query):
    index = source.find(query)

    if index == -1:
        return None

    return f"{index}:{index + len(query) - 1}"


def paginated_data_sb(source_url, data_key, headers, limit = 25, next = None):
    params = paginated_params(limit, None, next)

    response = requests.get(source_url, headers = headers, params = params)

    if response.status_code != 200:
        raise exceptions.BadAPIResponse(
            f"requesting {response.url} failed\n{response.text}")

    return {
        "items": response.json()[data_key],
        "paging": {
            "prev": None,
            "next": response.json().get("next")
        }
    }
