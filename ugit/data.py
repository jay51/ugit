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
    value = None
    if os.path.isfile(rel_path):
        with open(rel_path, "r") as f:
            value = f.read().strip()

    if value and value.startswith("ref:")
        return get_ref(value.split(":", 1)[1].strip())

    return value


def update_ref(ref, oid):
    # this is a hacky way to also be able to write tags to ugit/tags/<tagname>
    rel_path = f"{GIT_DIR}/{ref}"
    os.makedirs(os.path.dirname(rel_path), exist_ok=True)
    with open(rel_path, "w") as f:
        f.write(oid)

# yields relative path to all files in refs dir
def iter_refs():
    refs = ["HEAD"]
    for root, _, filenames in os.walk(f"{GIT_DIR}/refs/"):
        # get relative path of root, relative to {GIT_DIR}
        path = os.path.relpath(root, GIT_DIR)
        refs.extend(f"{path}/{name}" for name in filenames)

    for ref in refs:
        yield ref, get_ref(ref)
