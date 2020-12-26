# vanity.py - Brute-force a desired short commit ID in a Git repository

# Copyright (c) 2020 Christian Zietz

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import hashlib
import subprocess
import re
import os
import multiprocessing


if len(sys.argv) < 2:
    sys.exit("Usage: %s <desired-start-of-hash>" % sys.argv[0])

match = sys.argv[1].lower()
#match = "0000000"

# Support deprecated Python 2.7 by redefining 'range'
if sys.version_info[0] == 2:
    range = xrange

# Format the salt added to the commit message
def salt_fun(salt):
    return "\nSalt: "+hex(salt)+"\n"

# Initialization of pool processes: store the original commit data
def set_commit_info(arg):
    global ci
    ci = arg

# Create a commit object like Git would (adding the salt), hash it and check for a match
def force_hash(salt):
    global ci
    commit = ci+salt_fun(salt)
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
        sys.exit("Uncommitted changes exist in the working tree")

    # Get info about current HEAD commit
    commit_info = subprocess.check_output("git cat-file -p HEAD".split())
    if isinstance(commit_info, bytes):
        commit_info = commit_info.decode("utf-8")

    # Parse out info from the commit data returned by Git
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
    
    # Failed to find a solution?
    if res is None:
        sys.exit("FAILED! Found no salt that leads to ID: "+match)

    # Prepare a new commit replicating existing one (plus salt)
    os.environ["GIT_AUTHOR_NAME"] = author.group(1)
    os.environ["GIT_AUTHOR_EMAIL"] = author.group(2)
    os.environ["GIT_AUTHOR_DATE"] = author.group(3)

    os.environ["GIT_COMMITTER_NAME"] = committer.group(1)
    os.environ["GIT_COMMITTER_EMAIL"] = committer.group(2)
    os.environ["GIT_COMMITTER_DATE"] = committer.group(3)

    msg = msg + salt_fun(salt)
    msg = msg.encode("utf-8")

    # Create the new commit
    git_cmd = ["git", "commit-tree", tree]
    if parent is not None:
        git_cmd = git_cmd + ["-p", parent]
    git_proc = subprocess.Popen(git_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    new_hash = git_proc.communicate(msg)[0].decode("utf-8").strip()
    if new_hash != hash:
        sys.exit("FAILED! Expected ID: "+hash+". But got ID:"+new_hash)

    # Set working tree to new commit
    subprocess.call(["git", "reset", "--hard", new_hash])

    # Wait for pool to terminate
    p.join()