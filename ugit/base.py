import os
import pathlib
import itertools
import operator
import string
from collections import namedtuple
from . import data


# recursively hash and store the content of directory inside object DB
# And store all hashes, type of object and name for objects in new object with type tree
def write_tree (directory='.'):
    entries = []
    it = os.scandir(directory)
    for entry in it:
        full = f'{directory}/{entry.name}'
        if is_ignored(full): continue
        if entry.is_file(follow_symlinks=False):
            _type = "blob"
            with open(full, "rb") as f:
                oid = data.hash_object(f.read())
        elif entry.is_dir(follow_symlinks=False):
            _type = "tree"
            oid = write_tree(full)

        entries.append((entry.name, oid, _type))
    it.close()

    # Create the Tree object
    tree = "".join((f"{_type} {oid} {name}\n" for name, oid, _type in sorted(entries) ))
    print("WRITE TREE")
    print(tree)
    # oid of current directory which stores files and sub-trees oids
    return data.hash_object(tree.encode(), "tree")



# parse a tree object and yield _type, oid, name for each entry inside tree object
def _iter_tree_entries(oid):
    if not oid:
        return None
    tree = data.get_object(oid, "tree")
    for entry in tree.decode().splitlines():
        _type, oid, name = entry.split(" ", 2)
        yield _type, oid, name


# take tree oid and collects path and oid to each entry inside tree in a dict()
def get_tree(oid, base_path=""):
    result = dict()
    for _type, oid, name in _iter_tree_entries(oid):
        assert "/" not in name
        assert name not in ("..", ".")
        path = base_path + name
        if _type == "blob":
            result[path] = oid
        elif _type == "tree":
            result.update(get_tree(oid, f"{path}/"))
        else:
            assert False, f'Unknown tree entry {type_}'

    return result


# delete everything in the current directory except for ignored files
def _empty_current_directory():
    for root, dirnames, filenames in os.walk(".", topdown=False):
        for filename in filenames:
            path = os.path.relpath(f"{root}/{filename}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)

        for dirname in dirnames:
            path = os.path.relpath(f"{root}/{dirname}")
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                # deleting might fail if directory containes ignored files
                pass


# uses get_tree to get oids and path and write the content of each oid to working directory
def read_tree(tree_oid):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path="./").items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as out:
            _bytes = out.write(data.get_object(oid))
            print(f"writing {_bytes} bytes to {path}")


# calls write_tree, take oid returend and a message and store it as a new object in the database of type commit
def commit(msg):
    commit = f"tree {write_tree()}\n"
    HEAD = data.get_ref("HEAD")
    if HEAD:
        commit += f"parent {HEAD}\n"
    commit += "\n"
    commit += f"{msg}\n"
    oid = data.hash_object(commit.encode(), "commit")
    data.update_ref("HEAD", oid)
    return oid


# parse a commit object and return a commit tuple with tree, parent and msg of commit object
Commit = namedtuple("Commit", ["tree", "parent", "msg"])
def get_commit(oid, debug=False):
    commit = data.get_object(oid, "commit").decode()
    lines = iter(commit.splitlines())
    parent, tree = "", ""
    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(" ", 1)
        if key == "tree":
            tree = value
        elif key == "parent":
            parent = value
        else:
            assert False, f"Unkown Field {key}"

    msg = "\n".join(lines)
    c = Commit(tree=tree, parent=parent, msg=msg)
    if debug:
        print(c)
    return c


# get the commit information then read_tree of that commit and set the HEAD to point at that commit
def checkout(oid):
    commit = get_commit(oid)
    read_tree(commit.tree)
    data.update_ref("HEAD", oid)


# attach an oid to a name
def create_tag(name, oid):
    data.update_ref(f"refs/tags/{name}", oid)


# translate a name to oid or just return that oid if get_ref can't find it
def get_oid(name):
    name = "HEAD" if name == "@" else name
    refs_to_try = [
        f'{name}',
        f'refs/{name}',
        f'refs/tags/{name}',
        f'refs/heads/{name}',
    ]
    for ref in refs_to_try:
        ref = data.get_ref(ref)
        if ref is not None: return ref

    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name
    assert False, f"UNKOWN NAME {name}"


# yield all commits it can reach from a given set of commit oids in a random order and uses graphiz to link them
def iter_commits_and_parents(oids):
    oids = set(oids)
    visited = set()
    while oids:
        oid = oids.pop()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        oids.add(commit.parent)


# check if file or dir is ignored
def is_ignored(path):
    ignore = (".ugit", "env", ".git", "ugit")
    parts = pathlib.Path(path).parts
    for name in ignore:
        if name in parts: return True
