Test assertions
===============

A useful test assertion describes the complete behavior that must remain
stable. Comparing a whole response catches missing fields, unexpected fields,
and changed values in one place. It also produces a single diff that is easier
to review than a sequence of assertions against individual fields.

Not every value is stable, though. Database identifiers, UUIDs, timestamps,
and values close to a timing boundary are expected to change between test
runs. `inline-snapshot`_ and `dirty-equals`_ express this distinction:

.. list-table::
  :header-rows: 1
  :widths: 25 35 40

  * - Tool
    - Use it when
    - What it verifies
  * - `inline-snapshot`_
    - The complete value is deterministic and worth asserting.
    - The exact value, stored next to the assertion and reviewed as code.
  * - `dirty-equals`_
    - A value is generated at runtime or can vary for a known reason.
    - Its type, shape, format, range, or other relevant properties.

These tools are not alternatives. A snapshot can describe a stable container
while ``dirty-equals`` matchers describe its dynamic values.

.. tip::

  This guide focuses on choosing an assertion strategy and shows only a small
  set of features. Refer to the full `inline-snapshot documentation`_ and
  `dirty-equals documentation`_ for all supported snapshot operations,
  matchers, and configuration options.


Assert deterministic values with inline-snapshot
------------------------------------------------

Use ``snapshot()`` when every value in the expected result is deterministic.
Validation errors are a good example: the complete error response is part of
the API contract, including the number and order of errors, their locations,
messages, and types.

.. literalinclude:: /examples/testing/inline_snapshot_usage.py
  :caption: test_inline_snapshot.py
  :language: python
  :linenos:

One possible workflow is:

1. Write the assertion with an empty ``snapshot()`` call.
2. Run the focused test with ``--inline-snapshot=create`` or ``--fix``.
3. Inspect the generated value and its diff. A snapshot is expected test code,
   not an automatically approved result.
4. Run the test again normally. The committed literal is then compared exactly
   on every run.

Inline snapshots are especially convenient for nested dictionaries and lists:
the expected value stays beside the behavior it documents, and an intentional
contract change produces an ordinary source diff.

.. tip::

  ``inline-snapshot`` supports more workflows and value types than this basic
  example demonstrates. See the `inline-snapshot documentation`_ when you need
  to create, update, review, or make an existing snapshot more precise.


Describe dynamic values with dirty-equals
-----------------------------------------

Do not freeze a value that is supposed to change. Instead, use the narrowest
``dirty-equals`` matcher that describes the behavior the application promises.

.. literalinclude:: /examples/testing/dirty_equals_usage.py
  :caption: test_dirty_equals.py
  :language: python
  :linenos:

This assertion still checks the complete response. The UUID is not ignored:
``IsUUID(4)`` verifies both its format and version, while the deterministic
email and age remain exact. Matchers such as ``IsDatetime(iso_string=True)``,
``IsInt(gt=0)``, ``IsList(..., check_order=False)``, and ``IsOneOf(...)`` can
express other kinds of controlled variability. See the
`dirty-equals string matcher documentation`_ for options supported by
``IsStr()``.

Prefer the most precise matcher available. For example, ``IsUUID(4)`` states
more about an identifier than ``IsStr()``, and a bounded integer matcher states
more than accepting any number.

.. tip::

  ``dirty-equals`` includes specialized matchers for strings, numbers, dates,
  mappings, iterables, instances, and other common values. Browse the complete
  `dirty-equals documentation`_ before using a broad matcher; a more expressive
  matcher might already describe the property you need. The
  `dirty-equals string matcher documentation`_ shows, for example, how to
  constrain length, case, and regular expressions.


Combine exact snapshots and dynamic matchers
--------------------------------------------

Most real responses contain both stable and dynamic values. Keep the complete
stable structure in an inline snapshot and put ``dirty-equals`` matchers only
at the dynamic leaves.

.. literalinclude:: /examples/testing/combined_assertion_usage.py
  :caption: test_combined_assertion.py
  :language: python
  :linenos:

This composition gives the test both properties we want: changing the response
shape or a deterministic field produces a snapshot diff, while a newly
generated UUID remains valid without making the test flaky.


Choosing an assertion
---------------------

Start from the value you want to verify:

1. If the complete value is deterministic and meaningful, use an inline
   snapshot.
2. If the complete structure is dynamic, compare it directly with a structure
   containing ``dirty-equals`` matchers.
3. If the structure is stable but some leaves are dynamic, put the matchers
   inside an inline snapshot.
4. If output differs between supported implementations or environments, assert
   only their shared contract. Do not snapshot an implementation-specific
   message merely to make the current run pass.

Avoid weakening stable assertions with broad matchers. Conversely, do not
hard-code generated IDs or timestamps, normalize them into arbitrary constants,
or regenerate snapshots without reviewing why they changed.

.. _dirty-equals: https://dirty-equals.helpmanual.io/latest/
.. _dirty-equals documentation: https://dirty-equals.helpmanual.io/latest/
.. _dirty-equals string matcher documentation: https://dirty-equals.helpmanual.io/latest/types/string/
.. _inline-snapshot: https://15r10nk.github.io/inline-snapshot/latest/
.. _inline-snapshot documentation: https://15r10nk.github.io/inline-snapshot/latest/
