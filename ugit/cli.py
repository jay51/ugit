import os
import sys
import argparse
import textwrap
import subprocess
from . import data
from . import base

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
    checout_parser.add_argument("oid", type=oid, nargs="?")

    # tag a name to a commit oid or HEAD oid
    tag_parser = commands.add_parser("tag")
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument("name")
    tag_parser.add_argument("oid", default="@", type=oid, nargs="?")

    # visualize refs/commit history
    k_parser = commands.add_parser("k")
    k_parser.set_defaults(func=k)

    # `@` is an alias for HEAD
    # when you pass a tag or a name, it gets translated to oid in the parser
    return parser.parse_args()


def init(args):
    data.init()
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

def log(args):
    oid = args.oid
    while oid:
        commit = base.get_commit(oid)
        print(f"commit {oid}\n")
        print(textwrap.indent(commit.msg, "     "))
        print()
        oid = commit.parent

def checkout(args):
    if args.oid is not None:
        base.checkout(args.oid)
        print(f"on commit {args.oid}")

def tag(args):
    base.create_tag(args.name, args.oid)

def k(args):
    oids = set()
    dot = 'digraph commits {\n'
    for refname, ref in data.iter_refs():
        # print(refname, ref)
        dot += f'"{refname}" [shape=note]\n'
        dot += f'"{refname}" -> "{ref}"\n'
        oids.add(ref)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'
    dot += '}'

    with open("graph.dot", "w") as f:
        f.write(dot)
    subprocess.run(['dot', '-Tgtk', 'graph.dot'])
