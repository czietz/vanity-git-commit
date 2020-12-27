# vanity-git-commit
Modify an Git commit to have a desired short commit ID

This little Python script takes the `HEAD` commit from a local Git repository and tries to recreate an almost identical commit whose commit ID starts with a user-defined value. It does so by [salting](https://en.wikipedia.org/wiki/Salt_(cryptography)) the commit message. Since this is a brute-force process, it runs in parallel on all CPU cores. Like vanity license plates, these new commit IDs serve no practical purpose other than to look cool.

Example:
```
$ git log -n1
commit fbf49daafb8aa926ca6ef049b519d526966fafa6 (HEAD -> master)
Author: Christian Zietz <czietz@xxx.invalid>
Date:   Sat Dec 26 19:24:06 2020 +0000

    Make desired commit ID a command line parameter

    ... improve error handling and add license banner.

$ py vanity.py 1234567
12345670518f5235871775bc6cf2c2012136fe6a
HEAD is now at 12345670 Make desired commit ID a command line parameter

$ git log -n1
commit 12345670518f5235871775bc6cf2c2012136fe6a (HEAD -> master, origin/master)
Author: Christian Zietz <czietz@xxx.invalid>
Date:   Sat Dec 26 19:24:06 2020 +0000

    Make desired commit ID a command line parameter

    ... improve error handling and add license banner.

    Salt: 0xfed0c7d
```

Notes:
* This is merely a _toy_ program. I got the idea while reading [about how Git objects work](https://yurichev.com/news/20201220_git/).
* Surely, it could be optimized more.
* The longer the desired prefix is, the longer it will take to find a solution and the more likely it'll be that no solution can be found at all. However, the 7 character short commit IDs used by GitHub can be brute-forced in a few minutes on a modern machine. For an example, see https://github.com/czietz/vanity-git-commit/commit/1234567.
* If you want to undo the change, you can use `git reflog` to find the previous, i.e., unsalted commit ID, or you can immediately revert it with `git reset --hard HEAD@{1}`.
* **Use at your own risk!**
