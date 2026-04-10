# How to contribute


## Dependencies

We use [uv](https://github.com/astral-sh/uv) to manage the dependencies
and [just](https://github.com/casey/just) as a command runner.

To install `just` run:

```bash
uv tool install rust-just
```

To install project dependencies run:

```bash
uv sync --all-extras --all-groups
```

### venv

To activate your `virtualenv`
run `source .venv/bin/activate`.

### Compilation with mypyc, building a wheel

We also ship some optimized C-extensions together with our Python code.
If you want to build them run:

```bash
just mypyc
```

This will build `dmr.compiled` extensions
with [`mypyc`](https://mypyc.readthedocs.io/en/latest/).


## One magic command

After you installed the deps, run `just test` to run everything we have!

To see all available commands:

```bash
just
```


## Tests

To run tests:

```bash
just unit
```

To run linting:

```bash
just lint
```

These steps are mandatory during the CI.


## Documentation

To build docs locally:

```bash
just docs
```

If docs build fails on macOS with multiprocessing-related errors while
running examples, force the start method explicitly:

```bash
DMR_SPAWN_METHOD=spawn just docs
```


## Submitting your code

We use [trunk based](https://trunkbaseddevelopment.com/)
development (we also sometimes call it `wemake-git-flow`).

What is the point of this method?

1. We use protected `master` branch,
   so the only way to push your code is via pull request
2. We use issue branches: to implement a new feature or to fix a bug
   create a new branch named `issue-$TASKNUMBER`
3. Then create a pull request to `master` branch
4. We use `git tag`s to make releases, so we can track what has changed
   since the latest release

So, this way we achieve an easy and scalable development process
which frees us from merging hell and long-living branches.

In this method, the latest version of the app is always in the `master` branch.

### Before submitting

Before submitting your code please do the following steps:

1. Run `just test` to make sure everything was working before
2. Add any changes you want
3. Add tests for the new changes
4. Edit documentation if you have changed something significant
5. Update `CHANGELOG.md` with a quick summary of your changes
6. Run `just test` again to make sure it is still working


## Translations

We use Django's built-in i18n system. Translation files live in `dmr/locale/`.

### Contributing a new language

1. Generate a `.po` file for your [locale](https://docs.djangoproject.com/en/stable/topics/i18n/#term-locale-name):
   ```bash
   uv run django-admin makemessages --locale <lang>
   ```
2. Fill in the `msgstr` values in `dmr/locale/<lang>/LC_MESSAGES/django.po`
3. Compile and validate all translations:
   ```bash
   just translations
   ```
4. Commit both `django.po` and `django.mo` files

### Improving an existing translation

1. Edit `dmr/locale/<lang>/LC_MESSAGES/django.po`
2. Compile and validate:
   ```bash
   just translations
   ```
3. Commit both `django.po` and `django.mo` files


## Other help

You can contribute by spreading a word about this library.
It would also be a huge contribution to write
a short article on how you are using this project.
You can also share your best practices with us.
