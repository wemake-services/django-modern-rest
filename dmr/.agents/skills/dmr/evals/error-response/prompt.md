---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
tags: [smoke]
---

In my django-modern-rest controller the `get` method must answer
with a 404 and a JSON error body when the user does not exist.
Right now I return `HttpResponse(json.dumps({'detail': 'missing'}), status=404)`.
What is the idiomatic way to do this with dmr? Show the corrected method.
