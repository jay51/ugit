import os
import sys
import argparse
import textwrap
from . import data
from . import base

def main():
    args = parse_args()
    args.func(args)


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command")
    commands.required = True

    init_parser = commands.add_parser("init")
    init_parser.set_defaults(func=init)

    # given a file will hash, store and return oid
    hash_object_parser = commands.add_parser("hash_object")
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument("file")

    # give the object oid will print the file
    cat_file_parser = commands.add_parser("cat_file")
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument("oid")

    # given a directory will hash, store and return the oid of the directory
    write_tree_parser = commands.add_parser("write_tree")
    write_tree_parser.set_defaults(func=write_tree)

    # given a tree oid will parse entries inside object and write oids inside tree to working directory
    read_tree_parser = commands.add_parser("read_tree")
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument("tree")

    # stores the current dirctory in object database and stores the oid of current directory and message in DB
    commit_parser = commands.add_parser("commit")
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument("-m", "--message", required=True)

    # log commit history from HEAD or provided oid
    log_parser = commands.add_parser("log")
    log_parser.set_defaults(func=log)
    log_parser.add_argument("oid", nargs="?")

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
    # head always points to the last commit
    oid = args.oid or data.get_head()
    while oid:
        commit = base.get_commit(oid)
        print(f"commit {oid}\n")
        print(textwrap.indent(commit.msg, "     "))
        print()
        oid = commit.parent

