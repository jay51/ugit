import os
import sys
import argparse
import textwrap
import subprocess
from . import data
from . import base
from . import diff

def main():
    args = parse_args()
    args.func(args)


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command")
    commands.required = True
    oid = base.get_oid

    init_parser = commands.add_parser("init")
    init_parser.set_defaults(func=init)

    # given a file will hash, store and return oid
    hash_object_parser = commands.add_parser("hash_object")
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument("file")

    # give the object oid will print the file
    cat_file_parser = commands.add_parser("cat_file")
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument("oid", type=oid)

    # given a directory will hash, store and return the oid of the directory
    write_tree_parser = commands.add_parser("write_tree")
    write_tree_parser.set_defaults(func=write_tree)

    # given a tree oid will parse entries inside object and write oids inside tree to working directory
    read_tree_parser = commands.add_parser("read_tree")
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument("tree", type=oid)

    # stores the current dirctory in object database and stores the oid of current directory and message in DB
    commit_parser = commands.add_parser("commit")
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument("-m", "--message", required=True)

    # log commit history from HEAD or provided oid
    log_parser = commands.add_parser("log")
    log_parser.set_defaults(func=log)
    log_parser.add_argument("oid", default="@", type=oid, nargs="?")

    # write that commit tree to current directory and set HEAD to point at that commit
    checout_parser = commands.add_parser("checkout")
    checout_parser.set_defaults(func=checkout)
    checout_parser.add_argument("commit")

    # tag a name to a commit oid or HEAD oid
    tag_parser = commands.add_parser("tag")
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument("name")
    tag_parser.add_argument("oid", default="@", type=oid, nargs="?")

    # visualize refs/commit history
    k_parser = commands.add_parser("k")
    k_parser.set_defaults(func=k)

    # create new branch point to oid (default to HEAD)
    branch_parser = commands.add_parser("branch")
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument("name", nargs="?")
    branch_parser.add_argument("start_point", default="@", type=oid, nargs="?")

    # `@` is an alias for HEAD
    # when you pass a tag or a name, it gets translated to oid in the parser

    # print the current branch
    status_parser = commands.add_parser("status")
    status_parser.set_defaults(func=status)


    # change HEAD and the current branhc to point at the oid
    reset_parser = commands.add_parser("reset")
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument("commit", type=oid)

    # show diff of commit current commit and parent
    show_parser = commands.add_parser("show")
    show_parser.set_defaults(func=show)
    show_parser.add_argument("oid", default="@", type=oid, nargs="?")

    # diff the current working tree changes to a commit (not diff a commit to commit but a commit tot current changes)
    diff_parser = commands.add_parser("diff")
    diff_parser.set_defaults(func=_diff)
    diff_parser.add_argument("commit", default="@", type=oid, nargs="?")

    merge_parser = commands.add_parser("merge")
    merge_parser.set_defaults(func=merge)
    merge_parser.add_argument("commit", type=oid)

    return parser.parse_args()


def init(args):
    base.init()
    print (f'Initialized empty ugit repository in {os.getcwd()}/{data.GIT_DIR}')


def hash_object(args):
    with open(args.file, "rb") as f:
        print(data.hash_object(f.read()))

def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.oid, expected=None))

def write_tree(args):
    print("current Tree: ", base.write_tree())

def read_tree(args):
    base.read_tree(args.tree)

def commit(args):
    print("commit: ", base.commit(args.message))


def _print_commit(oid, commit, refs=None):
    refs_str = f' ({", ".join (refs)})' if refs else ""
    print(f"commit {oid} {refs_str})")
    print(textwrap.indent(commit.msg, "     "))
    print()


def log(args):
    # build a hashtable or oid key to value refnames pointing to oid
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)

    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))


def checkout(args):
    base.checkout(args.commit)
    print(f"on commit {args.commit}")

def tag(args):
    base.create_tag(args.name, args.oid)

def branch(args):
    if not args.name:
        curr = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = "*" if curr == branch else "  "
            print (f"{prefix} {branch}")
    else:
        base.create_branch(args.name, args.start_point)
        print(f"Branch {args.name} created at {args.start_point[:10]}")


def status(args):
    HEAD = base.get_oid("@")
    branch = base.get_branch_name()
    if branch:
        print(f"On branch {branch}")
    else:
        print(f"HEAD detached at {HEAD[:10]}")

    print("\n Changes to be commited:\n")
    HEAD_tree = HEAD and base.get_commit(HEAD).tree
    for path, action in diff.iter_changed_files(
                                            base.get_tree(HEAD_tree),
                                            base.get_working_tree()):
        print (f"{action:>12}: {path}")


def reset(args):
    base.reset(args.commit)


def show(args):
    if not args.oid:
        return None
    commit = base.get_commit(args.oid)
    parent_tree = None
    if commit.parent is not None:
        parent_tree = base.get_commit(commit.parent).tree

    _print_commit(args.oid, commit)
    result = diff.diff_trees(
        base.get_tree(parent_tree),
        base.get_tree(commit.tree)
    )
    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def _diff(args):
    tree = args.commit and base.get_commit(args.commit).tree

    # diff tree with args.commit.oid to current working tree
    result = diff.diff_trees(base.get_tree(tree), base.get_working_tree())
    sys.stdout.flush()
    sys.stdout.buffer.write(result)

def merge(args):
    base.merge(args.commit)

# write all refs and the commit a ref points to, then write history of commits and uses graphiz to link them
def k(args):
    oids = set()
    dot = 'digraph commits {\n'
    for refname, ref in data.iter_refs(deref=False):
        dot += f'"{refname}" [shape=note]\n'
        dot += f'"{refname}" -> "{ref.value}"\n'
        # add only refs to oid (not symbolic ref to another ref)
        if not ref.symbolic:
            oids.add(ref.value)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'
    dot += '}'

    with open("graph.dot", "w") as f:
        f.write(dot)
    subprocess.run(['dot', '-Tgtk', 'graph.dot'])
