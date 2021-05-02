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

# Add the salt to the commit
def salt_commit(meta,msg,salt):
    return meta+"\nhiddensalt "+hex(salt)+"\n\n"+msg

# Initialization of pool processes: store the original commit data
def set_commit_info(arg1,arg2):
    global meta
    global msg
    meta = arg1
    msg  = arg2

# Create a commit object like Git would (adding the salt), hash it and check for a match
def force_hash(salt):
    global meta
    global msg
    commit = salt_commit(meta,msg,salt)
    commit = ("commit %d\0"%len(commit.encode("utf-8")))+commit
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
    commit_info = commit_info.decode("utf-8")

    # Parse out info from the commit data returned by Git
    (meta,msg) = commit_info.split("\n\n", 1)
    # print(meta)
    # print(msg)

    # Brute-force hash on multiple CPUs
    p = multiprocessing.Pool(initializer=set_commit_info, initargs=(meta,msg))
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
    new_commit = salt_commit(meta,msg,salt)
    new_commit = new_commit.encode("utf-8")
    git_proc = subprocess.Popen("git hash-object -t commit -w --stdin".split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    new_hash = git_proc.communicate(new_commit)[0].decode("utf-8").strip()
    if new_hash != hash:
        sys.exit("FAILED! Expected ID: "+hash+". But got ID:"+new_hash)

    # Set working tree to new commit
    subprocess.call(["git", "reset", "--hard", new_hash])

    # Wait for pool to terminate
    p.join()