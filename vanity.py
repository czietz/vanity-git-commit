import sys
import hashlib
import subprocess
import re
import os
import multiprocessing

#match = "0000000"
match = "badc0de"

# Support deprecated Python 2.7 by redefining 'range'
if sys.version_info[0] == 2:
    range = xrange

def set_commit_info(arg):
    global ci
    ci = arg

def force_hash(salt):
    global ci
    commit = ci+"\nSalt: "+hex(salt)+"\n"
    commit = ("commit %d\0"%len(commit))+commit
    commit = commit.encode("utf-8")
    hash = hashlib.sha1(commit).hexdigest()
    if hash.startswith(match):
        return (salt,hash)
    else:
        return None


if __name__ == "__main__":
    # Check that no uncommitted changes exist
    if subprocess.call("git diff-index --quiet HEAD --".split()):
        raise(Exception("Uncommitted changes exist in the working tree"))

    # Get info about current HEAD commit
    commit_info = subprocess.check_output("git cat-file -p HEAD".split())
    if isinstance(commit_info, bytes):
        commit_info = commit_info.decode("utf-8")

    # Parse out info
    tree = re.search("tree ([0-9a-f]+)\n",commit_info).group(1)
    parent = re.search("parent ([0-9a-f]+)\n",commit_info)
    if parent is not None:
        parent = parent.group(1)
    author = re.search("author (.*) <(.*)> (.*)\n",commit_info)
    committer = re.search("committer (.*) <(.*)> (.*)\n",commit_info)
    msg = re.search("\n\n(.*)", commit_info, re.DOTALL).group(1)
    #print(tree)
    #print(parent)
    #print(author.groups())
    #print(committer.groups())
    #print(msg)

    # Brute-force hash on multiple CPUs
    p = multiprocessing.Pool(initializer=set_commit_info, initargs=(commit_info,))
    for res in p.imap_unordered(force_hash, range(0,2**31-1), 32768):
        if res is not None:
            (salt,hash) = res
            print(hash)
            break
    p.terminate()

    # Create new commit replicating existing one (plus salt)
    os.environ["GIT_AUTHOR_NAME"] = author.group(1)
    os.environ["GIT_AUTHOR_EMAIL"] = author.group(2)
    os.environ["GIT_AUTHOR_DATE"] = author.group(3)

    os.environ["GIT_COMMITTER_NAME"] = committer.group(1)
    os.environ["GIT_COMMITTER_EMAIL"] = committer.group(2)
    os.environ["GIT_COMMITTER_DATE"] = committer.group(3)

    msg = msg + "\nSalt: "+hex(salt)+"\n"
    msg = msg.encode("utf-8")

    # Create a new commit
    git_cmd = ["git", "commit-tree", tree]
    if parent is not None:
        git_cmd = git_cmd + ["-p", parent]
    git_proc = subprocess.Popen(git_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    new_hash = git_proc.communicate(msg)[0].decode("utf-8").strip()
    if new_hash != hash:
        raise(Exception("FAILED! Expected ID: "+hash+". But got ID:"+new_hash))

    # Set working tree to new commit
    subprocess.call(["git", "reset", "--hard", new_hash])

    p.join()