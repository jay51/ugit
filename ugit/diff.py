import subprocess
from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp
from . import data


# def x(*trees) is a function that accepts many arguments and put them in list
# returns dict of each file in tree as key and both trees' oid of file as value
def compare_trees(*trees):
    # Any key that does not exist gets the value returned by the default lambda 
    entries = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield path, *oids


# takes 2 oids, if they don't match, we call diff_blog on the 2
def diff_trees(t_from, t_to):
    output = b""
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            output += diff_blob(o_from, o_to)

    return output


def diff_blob(o_from, o_to, path="blob"):
    with Temp() as f_from, Temp() as f_to:
        for oid, f in ((o_from, f_from), (o_to, f_to)):
            if oid:
                f.write(data.get_object(oid))
                f.flush()

        with subprocess.Popen([
            "diff", "--unified", "--show-c-function",
            "--label", f"a/{path}", f_from.name,
            "--label", f"b/{path}", f_to.name],
            # "--label", f".ugit/objects/{o_from}", f_from.name, # also works but
            # "--label", f".ugit/objects/{o_to}", f_to.name],
            stdout=subprocess.PIPE
        ) as proc:
            output, _ = proc.communicate ()
    return output


def iter_changed_files(t_from, t_to):
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            action = (
                "new file" if not o_from else
                "deleted" if not o_to else
                "modified"
            )
        yield path, action


