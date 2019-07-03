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

def paginated_data(data, items):
    paging = paging = {
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
