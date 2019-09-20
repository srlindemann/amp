#!/bin/bash -e

# ```
# Report git cached and modified files.
# ```

# We don't wrap into exec since we pipe the output through other commands.

(git diff --cached --name-only; git ls-files -m) | sort | uniq | perl -ne 'print if /\S/'
#git status --porcelain 2>&1 | grep -v "?" | cut -f 3 -d ' '
