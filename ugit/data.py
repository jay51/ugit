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

def get_ref(ref):
    rel_path = f"{GIT_DIR}/{ref}"
    if os.path.isfile(rel_path):
        with open(rel_path, "r") as f:
            return f.read().strip()
    return None


def update_ref(ref, oid):
    # this is a hacky way to also be able to write tags to ugit/tags/<tagname>
    rel_path = f"{GIT_DIR}/{ref}"
    os.makedirs(os.path.dirname(rel_path), exist_ok=True)
    with open(rel_path, "w") as f:
        f.write(oid)
