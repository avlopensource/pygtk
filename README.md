# PyGTK for Python 3

This is a port of PyGTK to Python 3.

The immediate question is, of course, why. Why would anyone port abandoned PyGTK (and the required PyGObject 2) to Python 3 when the great new PyGObject-based bindings are available? Continuing to use the long-dead GTK 2 with Python 3?

Well... We had a _large_ Python 2 + PyGTK + GTK 2 codebase that we wanted to port to Python 3 and a newer GTK. Should we deal with Python 2 -> Python 3, PyGTK -> PyGObject and GTK 2 -> GTK 3 at the same time? In something created by many people working full-time over many years while continuing to develop the thing? That's a recipe for a disaster. After evaluating our options we decided to deal with Python migration first  (i.e. make the step to Python 3 + PyGTK + GTK 2) and switch to a newer GTK once that's settled. Hence PyGTK for Python 3.
