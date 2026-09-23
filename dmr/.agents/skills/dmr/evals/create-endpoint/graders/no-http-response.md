---
type: regex
pattern: 'return\s+(HttpResponse|JsonResponse)\('
match: not_contains
target: last_message
---
