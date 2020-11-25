import os
from . import data
from . import base


# Where to fetch the remote refs from
REMOTE_REFS_BASE = "refs/heads/"
# Where to save the remote refs
LOCAL_REFS_BASE = "refs/remote/"


def fetch(remote_path):
    # Get refs from server
    refs = _get_remote_refs(remote_path, REMOTE_REFS_BASE)

    # Fetch missing objects by iterating and fetching on demand
    for oid in base.iter_objects_in_commits(refs.values()):
        data.fetch_object_if_missing(oid, remote_path)
    # Update local refs to match server
    for remote_name, value in refs.items():
        refname = os.path.relpath(remote_name, REMOTE_REFS_BASE)
        data.update_ref(
            f"{LOCAL_REFS_BASE}/{refname}",
            data.RefValue(symbolic=False, value=value)
        )

# push all object files for a branch to a remote branch
def push(remote_path, refname):
    # Get refs data (oid)
    remote_refs = _get_remote_refs(remote_path)
    local_ref = data.get_ref(refname).value
    assert local_ref

    # Compute which objects the remote doesn't have
    known_remote_refs = filter(data.object_exist, remote_refs.values())
    remote_objects = set(base.iter_objects_in_commits(known_remote_refs))
    local_objects = set(base.iter_objects_in_commits({local_ref}))

    # outer left join
    objects_to_push = local_objects - remote_objects
    # Push all objects to remote
    for oid in objects_to_push:
        data.push_object(oid, remote_path)

    # Update remote ref to point at our target branch oid
    with data.change_git_dir(remote_path):
        data.update_ref(refname, data.RefValue(symbolic=False, value=local_ref))


def _get_remote_refs(remote_path, prefix=""):
    with data.change_git_dir(remote_path):
        return {refname: ref.value for refname, ref in data.iter_refs(prefix)}
