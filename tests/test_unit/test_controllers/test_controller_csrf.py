from http import HTTPStatus

from django.http import HttpResponse
from django.test import override_settings
from django.urls import reverse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import build_500_handler, path
from dmr.test import DMRClient


class _CsrfController(Controller[PydanticFastSerializer]):
    csrf_exempt = False

    def post(self) -> str:
        return 'ok'


urlpatterns = [
    path('api/csrf/', _CsrfController.as_view(), name='csrf'),
]
handler500 = build_500_handler('api/', serializer=PydanticFastSerializer)


# handler500 only works for `DEBUG=False` in Django.
@override_settings(ROOT_URLCONF=__name__, DEBUG=True)
def test_csrf_controller() -> None:
    """Ensure that `csrf_exempt=False` on controller is supported."""
    dmr_client = DMRClient(enforce_csrf_checks=True)

    response = dmr_client.post(reverse('csrf'), data={})

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.content == snapshot(
        b'<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta http-equiv="content-type" content="text/html; charset=utf-8">\n  <meta name="robots" content="NONE,NOARCHIVE">\n  <title>403 Forbidden</title>\n  <style>\n    html * { padding:0; margin:0; }\n    body * { padding:10px 20px; }\n    body * * { padding:0; }\n    body { font-family: sans-serif; background:#eee; color:#000; }\n    body>div { border-bottom:1px solid #ddd; }\n    h1 { font-weight:normal; margin-bottom:.4em; }\n    h1 span { font-size:60%; color:#666; font-weight:normal; }\n    #info { background:#f6f6f6; }\n    #info ul { margin: 0.5em 4em; }\n    #info p, #summary p { padding-top:10px; }\n    #summary { background: #ffc; }\n    #explanation { background:#eee; border-bottom: 0px none; }\n  </style>\n</head>\n<body>\n<div id="summary">\n  <h1>Forbidden <span>(403)</span></h1>\n  <p>CSRF verification failed. Request aborted.</p>\n\n\n  <p>You are seeing this message because this site requires a CSRF cookie when submitting forms. This cookie is required for security reasons, to ensure that your browser is not being hijacked by third parties.</p>\n  <p>If you have configured your browser to disable cookies, please re-enable them, at least for this site, or for \xe2\x80\x9csame-origin\xe2\x80\x9d requests.</p>\n\n</div>\n\n<div id="info">\n  <h2>Help</h2>\n    \n    <p>Reason given for failure:</p>\n    <pre>\n    CSRF cookie not set.\n    </pre>\n    \n\n  <p>In general, this can occur when there is a genuine Cross Site Request Forgery, or when\n  <a\n  href="https://docs.djangoproject.com/en/5.2/ref/csrf/">Django\xe2\x80\x99s\n  CSRF mechanism</a> has not been used correctly.  For POST forms, you need to\n  ensure:</p>\n\n  <ul>\n    <li>Your browser is accepting cookies.</li>\n\n    <li>The view function passes a <code>request</code> to the template\xe2\x80\x99s <a\n    href="https://docs.djangoproject.com/en/5.2/topics/templates/#django.template.backends.base.Template.render"><code>render</code></a>\n    method.</li>\n\n    <li>In the template, there is a <code>{% csrf_token\n    %}</code> template tag inside each POST form that\n    targets an internal URL.</li>\n\n    <li>If you are not using <code>CsrfViewMiddleware</code>, then you must use\n    <code>csrf_protect</code> on any views that use the <code>csrf_token</code>\n    template tag, as well as those that accept the POST data.</li>\n\n    <li>The form has a valid CSRF token. After logging in in another browser\n    tab or hitting the back button after a login, you may need to reload the\n    page with the form, because the token is rotated after a login.</li>\n  </ul>\n\n  <p>You\xe2\x80\x99re seeing the help section of this page because you have <code>DEBUG =\n  True</code> in your Django settings file. Change that to <code>False</code>,\n  and only the initial error message will be displayed.  </p>\n\n  <p>You can customize this page using the CSRF_FAILURE_VIEW setting.</p>\n</div>\n\n</body>\n</html>\n',
    )
