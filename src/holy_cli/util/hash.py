import hashlib


def hash_server_name(name: str) -> str:
    return hashlib.md5(name.encode("utf-8")).hexdigest()[0:16]
