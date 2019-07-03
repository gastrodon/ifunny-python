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
