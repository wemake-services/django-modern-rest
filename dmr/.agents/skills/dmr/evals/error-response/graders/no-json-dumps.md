---
type: regex
pattern: 'return[^\n]*json\.dumps\('
match: not_contains
target: last_message
---
