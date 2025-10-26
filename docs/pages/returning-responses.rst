Returning responses
===================

By default, all responses are validated at runtime to match the schema.
This allows us to be super strict about schema generation as a pro,
but as a con, it is slower than can possibly be.

You can disable response validation via configuration:
per endpoint, per controller, and globally.
