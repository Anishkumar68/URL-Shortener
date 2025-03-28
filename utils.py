import string

BASE62_ALPHABET = string.digits + string.ascii_letters


def encode_base62(num):
    """Convert an integer ID to a Base62 short string"""
    if num == 0:
        return BASE62_ALPHABET[0]
    encoded = []
    while num:
        num, rem = divmod(num, 62)
        encoded.append(BASE62_ALPHABET[rem])
    return "".join(reversed(encoded))
