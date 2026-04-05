try:
    from librt.base64 import b64encode
except ImportError:
    from base64 import b64encode


def basic_auth(username: str, password: str, *, prefix: str = 'Basic ') -> str:
    """
    Return a header value for basic auth for a given *username* and *password*.

    .. code:: python

      >>> basic_auth('admin', 'pass')
      'Basic YWRtaW46cGFzcw=='

      >>> basic_auth('admin', 'pass', prefix='')
      'YWRtaW46cGFzcw=='

    """
    return prefix + b64encode((username + ':' + password).encode()).decode()
