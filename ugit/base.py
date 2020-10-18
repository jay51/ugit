from . import data
import os
import pathlib


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


# calls write_tree, take oid returend and a message and store it as a new object in the database
def commit(msg):
    commit = f"tree {write_tree()}\n"
    HEAD = data.get_head()
    if HEAD:
        commit += f"parent {HEAD}\n"
    commit += "\n"
    commit += f"{msg}\n"
    oid = data.hash_object(commit.encode(), "commit")
    data.set_head(oid)
    return oid


# check if file or dir is ignored
def is_ignored(path):
    ignore = (".ugit", "env", ".git", "ugit")
    parts = pathlib.Path(path).parts
    for name in ignore:
        if name in parts: return True

