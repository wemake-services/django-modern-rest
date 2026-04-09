# Security Policy


## What we do to make security a top priority?

1. All the code that we own is analyzed
   with [Bandit](https://docs.astral.sh/ruff/rules/#flake8-bandit-s)
   security tool
2. We use strict [CodeQL](https://codeql.github.com) security checks on GitHub
3. We update our dependencies regularly, however, we use a cooldown of 7 days
   to limit the chances of a 0 day vulnerability
4. We check for known CVEs in our dependencies using [`uv audit`](https://docs.astral.sh/uv/reference/cli/#uv-audit)
   tool and GitHub's [Dependabot security audit](https://docs.github.com/en/code-security/concepts/security-at-scale/auditing-security-alerts)
   feature
5. We do not allow AI generated slop to pollute the repository
6. We follow all RFCs and guidelines for the features we expose
7. We don't write anything from scratch, if we use JWT feature,
   we use `pyjwt` as a trusted dependency
8. We minimize the number of runtime dependencies
9. We use [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers)
10. We use strict analysis of our CI jobs with [`zizmor`](https://docs.zizmor.sh),
    we pin all the actions to exact hashes
11. We do not disclose 0 day security issues publicly


## Security audits of your project

Do you have a Python / Django project that you need
to audit for security / performance?

Who will help you?

- [CPython Core Developer](https://github.com/python/cpython/pulls/sobolevn)
- [Django Software Foundation member](https://www.djangoproject.com/foundation/individual-members/)
- Maintainer of dozens of other opensource projects
- This project's original author :)

Drop [me](https://github.com/sobolevn) a line: `mail at sobolevn dot me`.
I do consulting for 10+ years now, so I can surely help your company.


## Reporting a Vulnerability

We take security vulnerabilities very seriously.
To reach the response team, fill in our vulnerability form at
https://github.com/wemake-services/django-modern-rest/security/advisories/new

Only the response team members will see your report,
and it will be treated confidentially.

The security team does not accept reports that only affect pre-release versions
of software, as these features are considered "in-development",
please open public issues.

The security team does not accept reports for third-party packages.
Or scope is limited to `django-modern-rest` only.
Those reports should be directed towards their
corresponding distribution security contact.

Please, read our [AI Policy](https://github.com/wemake-services/django-modern-rest/blob/master/.github/AI_POLICY.md)
before submitting reports made with the use of AI / LLM tools.


## Vulnerability handling

The following is an overview of the vulnerability handling process
from reporting to disclosure:

- The reporter reports the vulnerability privately to the security team.
- If the security team determines the report isn't a vulnerability,
  the issue can be opened in a public issue tracker if applicable.
- If the report constitutes a vulnerability, the security team will work
  privately with the reporter to resolve the vulnerability.
- The project creates a new release to deliver the fix.
- The project publicly announces the vulnerability and describes
  how to apply the fix via an advisory. At this point the vulnerability
  can be discussed publicly by the reporter and team.


## Bug bounties

While we sincerely appreciate and encourage reports of suspected security
problems, please note that the project does not run any bug bounty programs.
We are an opensource project, depending on donation
and support from the community.
