# Compiled subfolder

Everything in this directory is compiled with `mypyc` for some extra free speed.

**Do not** import modules from here directly.
Unless you know what you are doing.

But, we still provide a fallback to regular Python code:
1. Some platforms might not support our compiled wheels
2. Some runtimes run Python code faster than compiled
3. Some people might prefer to monkeypatch something in regular Python code

See https://django-modern-rest.readthedocs.io/en/latest/pages/deep-dive/performance.html#mypyc-compilation for more info.
