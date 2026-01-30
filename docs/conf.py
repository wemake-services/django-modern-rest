# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from docutils.nodes import Node
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx

# We need `server` to be importable from here:
_ROOT = Path('..').resolve(strict=True)
sys.path.insert(0, str(_ROOT))


# -- Project information -----------------------------------------------------


def _get_project_meta() -> dict[str, str]:
    pyproject = _ROOT / 'pyproject.toml'
    return cast(
        dict[str, str],
        tomllib.loads(pyproject.read_text())['tool']['poetry'],
    )


pkg_meta = _get_project_meta()
project = str(pkg_meta['name'])
copyright = '2025, wemake-services'  # noqa: A001
author = 'wemake-services'

# The short X.Y version
version = str(pkg_meta['version'])
# The full version, including alpha/beta/rc tags
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.intersphinx',
    # https://github.com/executablebooks/MyST-Parser
    'myst_parser',
    # 3rd party, order matters:
    'sphinx_design',
    'sphinx_copybutton',
    'sphinx_contributors',
    'sphinx_tabs.tabs',
    'sphinx_iconify',
    'sphinxcontrib.mermaid',
    # custom extensions
    'docs.tools.sphinx_ext',
]


# Intersphinx:
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'django': ('https://docs.djangoproject.com/en/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
    'msgspec': ('https://jcristharif.com/msgspec/', None),
}

# Napoleon:
napoleon_google_docstring = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_attr_annotations = True

# If true, Sphinx will warn about all references
# where the target cannot be found. Default is `False``.
# You can activate this mode temporarily using the `-n` command-line switch.
nitpicky = True

PY_CLASS = 'py:class'
nitpick_ignore = [
    # internal type helpers
    (PY_CLASS, 'FromJson'),
    (PY_CLASS, 'django_modern_rest.endpoint._ResponseT'),
    (PY_CLASS, 'django_modern_rest.endpoint._ModifyAnyCallable'),
    (PY_CLASS, 'django_modern_rest.endpoint._ModifyAsyncCallable'),
    (PY_CLASS, 'django_modern_rest.endpoint._ModifySyncCallable'),
    (PY_CLASS, '_ParamT'),
    (PY_CLASS, 'django_modern_rest.response._ItemT'),
    (PY_CLASS, 'django_modern_rest.internal.middleware_wrapper._TypeT'),
    (PY_CLASS, '_SerializerT'),
    (PY_CLASS, '_BlueprintT'),
    (PY_CLASS, 'SyncErrorHandlerT'),
    (PY_CLASS, 'AsyncErrorHandlerT'),
    (PY_CLASS, '_MethodSyncHandler'),
    (PY_CLASS, '_MethodAsyncHandler'),
    (PY_CLASS, 'django_modern_rest.decorators._ReturnT'),
    (PY_CLASS, 'django_modern_rest.decorators._ViewT'),
    (PY_CLASS, 'django_modern_rest.decorators._TypeT'),
    (PY_CLASS, 'django_modern_rest.internal.negotiation.ConditionalType'),
    (PY_CLASS, 'django_modern_rest.controller._SerializerT_co'),
    ('py:obj', 'django_modern_rest.controller._SerializerT_co'),
    # Undocumented in Django:
    (PY_CLASS, 'django.urls.resolvers.URLPattern'),
    (PY_CLASS, 'django.urls.resolvers.URLResolver'),
    # OpenAPI types used in TYPE_CHECKING blocks:
    (PY_CLASS, 'SecurityRequirement'),
    (PY_CLASS, 'ExternalDocumentation'),
    (PY_CLASS, 'Callback'),
    (PY_CLASS, 'Server'),
    (PY_CLASS, 'Reference'),
    (PY_CLASS, 'Paths'),
    (PY_CLASS, 'Responses'),
]

qualname_overrides = {
    # Django documents these classes under re-exported path names:
    'django.http.request.HttpRequest': 'django:django.http.HttpRequest',
    'django.http.response.HttpResponse': 'django:django.http.HttpResponse',
    'django.http.response.HttpResponseBase': (
        'django:django.http.HttpResponseBase'
    ),
}

# Set `typing.TYPE_CHECKING` to `True`:
# https://pypi.org/project/sphinx-autodoc-typehints/
set_type_checking_flag = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = ['.rst', '.md']

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'README.md']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'shibuya'
html_favicon = '_static/images/favicon.svg'

html_theme_options = {
    'github_url': 'https://github.com/wemake-services/django-modern-rest',
    'readthedocs_url': 'https://django-modern-rest.readthedocs.io',
    'globaltoc_expand_depth': 1,
    'nav_links': [
        {
            'title': 'Ask DeepWiki',
            'url': 'https://deepwiki.com/wemake-services/django-modern-rest',
        },
    ],
    'accent_color': 'green',
    'light_logo': '_static/images/logo-light.svg',
    'dark_logo': '_static/images/logo-dark.svg',
    'og_image_url': 'https://repository-images.githubusercontent.com/1072817092/f0ab70e3-c165-485b-b591-e860c16f7c4f',
}

html_context = {
    'source_type': 'github',
    'source_user': 'wemake-services',
    'source_repo': 'django-modern-rest',
    'source_version': 'master',
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_js_files = [
    'https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js',
]


def resolve_canonical_names(app: Sphinx, doctree: Node) -> None:
    """Resolve canonical names of types to names that resolve in intersphinx.

    Projects often document functions/classes under a name that is re-exported.
    For example, cryptography documents "Certificate"
    under ``cryptography.x509.Certificate``, but it's actually implemented in
    ``cryptography.x509.base.Certificate`` (and re-exported in x509.py).

    When Sphinx encounters typehints it tries to create links to the types,
    looking up types from external projects using ``sphinx.ext.intersphinx``.
    The lookup for such re-exported types fails because Sphinx
    tries to look up the object in the implemented ("canonical") location.

    .. seealso::

        * https://github.com/sphinx-doc/sphinx/issues/4826 - solves this
            with the "canonical" directive
        * https://github.com/pyca/cryptography/pull/7938 - where this
            was fixed for cryptography
        * https://www.sphinx-doc.org/en/master/extdev/appapi.html#events
        * https://stackoverflow.com/a/62301461 - source of this hack

    """
    pending_xrefs: Iterable[pending_xref] = doctree.findall(
        condition=pending_xref,
    )
    for node in pending_xrefs:
        alias = node.get('reftarget')
        if alias is None:
            continue

        if alias in qualname_overrides:
            node['reftarget'] = qualname_overrides.get(alias)


def setup(app: Sphinx) -> None:
    """Add hook functions to Sphinx hooks."""
    app.connect('doctree-read', resolve_canonical_names)
