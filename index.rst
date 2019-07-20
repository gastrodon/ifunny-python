iFunny python interface
=======================


Requirements:
    - requests
    - websocket-client
    - Python 3.7+

This is a python library aiming to interface with python. To learn more about the project, and to view it's code, check it out on `github <https://github.com/basswaver/ifunny>`_.

About
-----

This library can do a number of things in the scope of interacting with iFunny, though it is still very much in development and not (even close to) everything is implemented. This bot is also able to interface with ifunny chat (which just looks to be a modified client of sendbird) in a way idomatic to Python.

Though you can interface with raw responses, this lib provides a number of decorators for chat events (with more on the way), as well as decorators for commands executed with prefixes (very much so inspired by discordpy). The chat client is ran in it's own thread (unless specified not to, see debugging docs) and each messages triggers an event (again, in a separate thread)

Examples
--------

To create a simple chat bot, the most important steps are as follows
- create a client and authenticate it
- create a command method and decorate it
- start the chat thread (you can do this in any order, but it's probably best if you create your commands first)

A simple echo bot might look like this::

    from ifunny import Client
    robot = Client(prefix = "/")
    robot.login("email", "password")

    @robot.event(name = "on_connect")
    def _connected_to_chat(data):
        print("I'm connected")

    @robot.command(name = "echo")
    def _reply_with_same(message, args):
        message.send(f"You said {message.content}")

    me.start_chat()

There's still much more to do, so feel free to create a pull. If you want to find me, my discord is Zero#5200. You can also join a guild with me `here <https://discordapp.com/invite/h3ZnhRM>`_.

.. toctree::
   :maxdepth: 4
   :caption: Contents:

   code


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
