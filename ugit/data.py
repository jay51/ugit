import os
import hashlib


GIT_DIR = ".ugit"
GIT_OBJECTS = ".ugit/objects"


def init():
    if not os.path.isdir(GIT_DIR):
        os.makedirs(GIT_DIR)
        os.makedirs(GIT_OBJECTS)

def hash_object(data, _type="blob"):
    data = _type.encode() + b"\x00" + data
    oid = hashlib.sha1(data).hexdigest()
    with open(f"{GIT_OBJECTS}/{oid}", "wb") as out:
        out.write(data)
        return oid

def get_object(oid, expected="blob"):
    with open(f"{GIT_OBJECTS}/{oid}", "rb") as f:
        obj = f.read()

    _type, _, content = obj.partition(b"\x00")
    _type = _type.decode()
    if expected is not None:
        assert _type == expected, f"Expected {expected}, got {_type}"
    return content

