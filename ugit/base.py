import os
import pathlib
import itertools
import operator
import string
from collections import deque, namedtuple
from . import data
from . import diff


def init():
    data.init()
    data.update_ref("HEAD", data.RefValue(symbolic=True, value="refs/heads/master"))


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


# traverse current directory, write each file to DB and store file in a hashtable
def get_working_tree():
    result = {}
    for root, _, filenames in os.walk("."):
        for filename in filenames:
            path = os.path.relpath(f"{root}/{filename}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                result[path] = data.hash_object(f.read())

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
    HEAD = data.get_ref("HEAD").value
    if HEAD:
        commit += f"parent {HEAD}\n"
    MERGE_HEAD = data.get_ref("MERGE_HEAD").value
    if MERGE_HEAD:
        commit += f"parent {MERGE_HEAD}\n"
        data.delete_ref("MERGE_HEAD", deref=False)
    commit += "\n"
    commit += f"{msg}\n"
    oid = data.hash_object(commit.encode(), "commit")
    data.update_ref("HEAD", data.RefValue(symbolic=False, value=oid))
    return oid


def merge(other):
    HEAD = data.get_ref("HEAD").value
    assert HEAD
    c_HEAD = get_commit(HEAD)
    c_other = get_commit(other)
    data.update_ref("MERGE_HEAD", data.RefValue(symbolic=False, value=other))
    read_tree_merged(c_HEAD.tree, c_other.tree)
    print("Merged in working tree\nPlease commit")



# given 2 trees, will merge and write to working dir
def read_tree_merged(t_HEAD, t_other):
    _empty_current_directory()
    for path, blob in diff.merge_trees(get_tree(t_HEAD), get_tree(t_other)).items():
        os.makedirs(f"./{os.path.dirname(path)}", exist_ok=True)
        with open(path, "wb") as f:
            f.write(blob)


# parse a commit object and return a commit tuple with tree, parent and msg of commit object
Commit = namedtuple("Commit", ["tree", "parents", "msg"])
def get_commit(oid, debug=False):
    commit = data.get_object(oid, "commit").decode()
    lines = iter(commit.splitlines())
    parents, tree = [], ""
    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(" ", 1)
        if key == "tree":
            tree = value
        elif key == "parent":
            parents.append(value)

        else:
            assert False, f"Unkown Field {key}"

    msg = "\n".join(lines)
    c = Commit(tree=tree, parents=parents, msg=msg)
    if debug:
        print(c)
    return c


# get the commit information then read_tree of that commit and set the HEAD to point at that commit
def checkout(name):
    # if branch name  return oid for branch. if oid return same oid
    oid = get_oid(name)
    commit = get_commit(oid)
    read_tree(commit.tree)

    if is_branch (name):
        HEAD = data.RefValue(symbolic=True, value=f"refs/heads/{name}")
    else:
        HEAD = data.RefValue(symbolic=False, value=oid)

    data.update_ref("HEAD", HEAD, deref=False)


# changes HEAD and the current branch to point at the oid
def reset(oid):
    data.update_ref("HEAD", data.RefValue(symbolic=False, value=oid))


# attach an oid to a name
def create_tag(name, oid):
    data.update_ref(f"refs/tags/{name}", data.RefValue(symbolic=False, value=oid))


# attach an oid to a branch name
def create_branch(name, oid):
    data.update_ref(f"refs/heads/{name}", data.RefValue(symbolic=False, value=oid))


def is_branch(branch):
    return data.get_ref(f"refs/heads/{branch}").value is not None


def get_branch_name():
    HEAD = data.get_ref("HEAD", deref=False)
    # if HEAD is not symbolic, it means it's detached HEAD bc/ we always need to point to a branch
    if not HEAD.symbolic:
        return None
    HEAD = HEAD.value
    assert HEAD.startswith("refs/heads/")
    return os.path.relpath(HEAD, "refs/heads")


def iter_branch_names():
    for refname, _ in data.iter_refs("refs/heads"):
        yield os.path.relpath(refname, "refs/heads")


# translate a name to oid or just return that oid if get_ref can't find it
def get_oid(name):
    name = "HEAD" if name == "@" else name
    refs_to_try = [
        f"{name}",
        f"refs/{name}",
        f"refs/tags/{name}",
        f"refs/heads/{name}",
    ]
    for ref in refs_to_try:
        if data.get_ref(ref, deref=False).value:
            return data.get_ref(ref, deref=True).value

    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name
    assert False, f"UNKOWN NAME {name}"


# yield all commits it can reach from a given set of commit oids in order (DFS on a commit history)
def iter_commits_and_parents(oids):
    oids = deque(oids)
    visited = set()
    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        # RETURN FIRST PARENT NEXT
        oids.extendleft(commit.parents[:1])
        # RETURN OTHER PARENTS LATER
        oids.extend(commit.parents[1:])


# check if file or dir is ignored
def is_ignored(path):
    ignore = (".ugit", "env", ".git", "ugit")
    parts = pathlib.Path(path).parts
    for name in ignore:
        if name in parts: return True
