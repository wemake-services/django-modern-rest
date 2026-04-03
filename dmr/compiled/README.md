# Compiled subfolder

Everything in this directory is compiled with `mypyc` for some extra free speed.

**Do not** import modules from here directly.
Unless you know what you are doing.

But, we still provide a fallback to regular Python code:
1. Some platforms might not support our compiled wheels
2. Some runtimes run Python code faster than compiled
3. Some people might prefer to monkeypatch something in regular Python code

## What we compile

We only compile code that makes sense to be compiled.
Criteria:
1. Does not have IO
2. Does not have a lot of compiled / uncompiled context switches. For example,
   compiled code that frequently calls Python code
   will most like be slower in the result
3. Is executed on the hot path. Not in import time,
   but in request's handing phase
4. Is rather simple and does not have a lot of magic,
   otherwise - compilation will not have much effect
5. Does not have complex typing
6. Have no external dependencies
