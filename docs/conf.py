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
from typing import Final, cast

from docutils.nodes import Node
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx

# We need `dmr` to be importable from here:
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
    'sphinx_llms_txt',
    # custom extensions
    'docs.tools.sphinx_ext',
]


# Intersphinx:
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'django': ('https://docs.djangoproject.com/en/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
    'msgspec': ('https://jcristharif.com/msgspec/', None),
    'jwt': ('https://pyjwt.readthedocs.io/en/latest/', None),
    'typing_extensions': (
        'https://typing-extensions.readthedocs.io/en/stable/',
        None,
    ),
    'attrs': ('https://www.attrs.org/en/stable/', None),
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

_PY_CLASS: Final = 'py:class'
_PY_OBJ: Final = 'py:obj'

nitpick_ignore = [
    # internal type helpers
    (_PY_CLASS, 'FromJson'),
    (_PY_CLASS, 'dmr.endpoint._ResponseT'),
    (_PY_CLASS, 'dmr.endpoint._ModifyAnyCallable'),
    (_PY_CLASS, 'dmr.endpoint._ModifyAsyncCallable'),
    (_PY_CLASS, 'dmr.endpoint._ModifySyncCallable'),
    (_PY_CLASS, '_ParamT'),
    (_PY_CLASS, 'dmr.response._ItemT'),
    (_PY_CLASS, 'dmr.internal.middleware_wrapper._TypeT'),
    (_PY_CLASS, '_SerializerT'),
    (_PY_CLASS, 'SyncErrorHandler'),
    (_PY_CLASS, 'AsyncErrorHandler'),
    (_PY_CLASS, '_MethodSyncHandler'),
    (_PY_CLASS, '_MethodAsyncHandler'),
    (_PY_CLASS, 'BlocklistedJWToken'),
    (_PY_CLASS, '_StrOrPromise'),
    (_PY_CLASS, 'dmr.validation.response._ResponseT'),
    (_PY_CLASS, 'dmr.decorators._ReturnT'),
    (_PY_CLASS, 'dmr.decorators._ViewT'),
    (_PY_CLASS, 'dmr.decorators._TypeT'),
    (_PY_CLASS, 'dmr.internal.negotiation.ConditionalType'),
    (_PY_CLASS, 'dmr.security.jwt.views._ObtainTokensT'),
    (_PY_CLASS, 'dmr.security.jwt.views._TokensResponseT'),
    (
        _PY_CLASS,
        'dmr.security.django_session.views._RequestModelT',
    ),
    (_PY_CLASS, 'dmr.security.django_session.views._ResponseT'),
    (_PY_OBJ, 'dmr.components._HeadersT'),
    (_PY_OBJ, 'dmr.components._QueryT'),
    (_PY_OBJ, 'dmr.components._PathT'),
    (_PY_OBJ, 'dmr.components._BodyT'),
    (_PY_OBJ, 'dmr.components._CookiesT'),
    (_PY_OBJ, 'dmr.components._FileMetadataT'),
    (_PY_CLASS, 'dmr.pagination._ModelT'),
    (_PY_CLASS, 'dmr.controller._SerializerT_co'),
    (_PY_OBJ, 'dmr.controller._SerializerT_co'),
    (_PY_OBJ, 'dmr.streaming.sse.controller._SerializerT_co'),
    (_PY_CLASS, 'dmr.streaming.sse.controller._SerializerT_co'),
    (_PY_CLASS, 'dmr.streaming.controller._SerializerT_co'),
    (_PY_OBJ, 'dmr.streaming.jsonl.controller._SerializerT_co'),
    (_PY_CLASS, 'dmr.streaming.jsonl.controller._SerializerT_co'),
    (_PY_CLASS, 'dmr.streaming.sse.metadata._DataT_co'),
    # Explicitly protected names:
    (_PY_CLASS, 'dmr.parsers._NoOpParser'),
    (_PY_CLASS, 'dmr.streaming.controller._StreamingEndpoint'),
    # Unsolvable imports:
    (_PY_CLASS, 'AbstractBaseUser'),
    # Undocumented in Django:
    (_PY_CLASS, 'django.urls.resolvers.URLPattern'),
    (_PY_CLASS, 'django.urls.resolvers.URLResolver'),
    (_PY_CLASS, 'django.utils.datastructures.MultiValueDict'),
    (_PY_CLASS, 'django.utils.functional.Promise'),
    # OpenAPI types used in TYPE_CHECKING blocks:
    (_PY_CLASS, 'SecurityRequirement'),
    (_PY_CLASS, 'ExternalDocumentation'),
    (_PY_CLASS, 'Callback'),
    (_PY_CLASS, 'Server'),
    (_PY_CLASS, 'Reference'),
    (_PY_CLASS, 'Paths'),
    (_PY_CLASS, 'Responses'),
    # Looks like a bug:
    (_PY_CLASS, 'dict[str'),
    (_PY_CLASS, 'collections.abc.Mapping[str'),
]

qualname_overrides = {
    # Django documents these classes under re-exported path names:
    'django.http.request.HttpRequest': 'django:django.http.HttpRequest',
    'django.http.response.HttpResponse': 'django:django.http.HttpResponse',
    'django.http.response.HttpResponseRedirect': (
        'django:django.http.HttpResponseRedirect'
    ),
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

html_show_sourcelink = False
html_sourcelink_suffix = ''
llms_txt_uri_template = '{base_url}{docname}.html'


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
