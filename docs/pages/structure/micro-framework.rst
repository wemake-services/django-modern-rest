Micro-framework out of Django
=============================

Single file Django
------------------

You don't need microframeworks to build small APIs, because
Django is a microframework itself. With the only difference: it scales!

.. literalinclude:: /examples/structure/micro_framework/single_file_asgi.py
   :language: python
   :linenos:


Scaling it for real projects
----------------------------

However, all projects tend to grow while they are alive.
Microframeworks handle the scale poorly, because
they are not designed for this task.

We recommend using https://github.com/wemake-services/wemake-django-template
to set up production ready Django boilerplate code with all the best practices.

It can handle any scale!
