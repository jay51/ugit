import os
import hashlib
from collections import namedtuple


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


RefValue = namedtuple("RefValue", ["symbolic", "value"])

def get_ref(ref, deref=True):
    return _get_ref_internal(ref, deref)[1]


# delete a ref by removing the branch file that stores oid to commit (not removing object in DB)
def delete_ref(ref, deref=True):
    ref = _get_ref_internal(ref, deref)[0]
    os.remove(f"{GIT_DIR}/{ref}")


# return the ref (path to a branch) and its symbolic ref or oid (if deref=true) of a tag or a branch
def _get_ref_internal(ref, deref=True):
    rel_path = f"{GIT_DIR}/{ref}"
    value = None
    if os.path.isfile(rel_path):
        with open(rel_path, "r") as f:
            value = f.read().strip()

    symbolic = bool(value) and value.startswith("ref:")
    if symbolic:
        value = value.split(":", 1)[1].strip()
        if deref:
            return _get_ref_internal(value, deref=True)

    return ref, RefValue(symbolic=symbolic, value=value)


def update_ref(ref, value, deref=True):
    # this will return what HEAD is pointing to e.g. /refs/heads/master
    ref = _get_ref_internal(ref, deref)[0]
    assert value.value
    if value.symbolic:
        value = f"ref: {value.value}"
    else:
        value = value.value

    rel_path = f"{GIT_DIR}/{ref}"
    os.makedirs(os.path.dirname(rel_path), exist_ok=True)
    with open(rel_path, "w") as f:
        f.write(value)

# yields relative path to all files in refs dir
def iter_refs(prefix="", deref=False):
    refs = ["HEAD", "MERGE_HEAD"]
    for root, _, filenames in os.walk(f"{GIT_DIR}/refs/"):
        # get relative path of root, relative to {GIT_DIR}
        path = os.path.relpath(root, GIT_DIR)
        refs.extend(f"{path}/{name}" for name in filenames)

    for ref_name in refs:
        if not ref_name.startswith(prefix):
            continue
        ref = get_ref(ref_name, deref=deref)
        if ref.value:
            yield ref_name, ref
