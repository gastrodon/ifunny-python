import requests

mime_types = {
    "png"   : "image/png",
    "jpg"   : "image/jpeg",
    "jpeg"  : "image/jpeg",
    "jpe"   : "image/jpeg",
    "bmp"   : "image/bmp",
    "midi"  : "audio/midi",
    "mpeg"  : "video/mpeg",
    "oog"   : "video/oog",
    "webm"  : "video/webm",
    "wav"   : "audio/wav"
}

def determine_mime(url, bias = "image/png"):
    global mime_types
    return mime_types.get(url.split(".")[-1], bias)

def invalid_type(name, type, valid):
    return Exception(f"{name} must be of type {', '.join(valid)}, not {type}")

def paginated_format(data, items):
    paging = {
        "prev":     data["paging"]["cursors"]["prev"] if data["paging"]["hasPrev"] else None,
        "next":     data["paging"]["cursors"]["next"] if data["paging"]["hasNext"] else None
    }

    return {
        "items":    items,
        "paging":   paging
    }

def paginated_params(limit, prev, next):
    params = {
        "limit":    limit
    }

    if next:
        params["next"] = next
    elif prev:
        params["prev"] = prev

    return params

def paginated_data(source_url, data_key, headers, limit = 25, prev = None, next = None):
    params = paginated_params(limit, prev, next)

    response = requests.get(source_url, headers = headers, params = params)

    if response.status_code != 200:
        raise BadAPIResponse(f"requesting {response.url} failed\n{response.text}")

    return response.json()["data"][data_key]

def paginated_generator(source):
    buffer = source()

    while True:
        for item in buffer["items"]:
            yield item

        if not buffer["paging"]["next"]:
            break

        buffer = source(next = buffer["paging"]["next"])

def get_slice(source, query):
    index = source.find(query)

    if index == -1:
        return None

    return f"{index}:{index + len(query) - 1}"

def paginated_data_sb(source_url, data_key, headers, limit = 25, next = None):
    params = paginated_params(limit, None, next)

    response = requests.get(source_url, headers = headers, params = params)

    if response.status_code != 200:
        raise BadAPIResponse(f"requesting {response.url} failed\n{response.text}")

    return {
        "items": response.json()[data_key],
        "paging": {
            "prev": None,
            "next": response.json().get("next")
        }
    }
