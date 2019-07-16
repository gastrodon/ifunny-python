def _default(message, args):
    return

def _help(message, args):
    """
    List commands
    """
    _help = f"my prefixes are {', '.join(list(message.client.prefix))}"
    for command in message.client.commands:
        command = message.client.commands[command]
        _help += f"{command.name}: {command.help if command.help else 'no docstring'}\n"

    message.send(_help)

class Command:
    def __init__(self, method, name, cog = None):
        self.method = method
        self.name = name
        self.help = self.method.__doc__
        cog = cog

    def __call__(self, message, args):
        return self.method(message, args)

class Defaults:

    help = Command(_help, "help")

    default = Command(_default, "default")

class Cog:
    bot = None
    name = None
    commands = {}

    def command(cls, name = None):
        """
        Decorator to add a command to a cog. Works in the way as ``bot.command``
        """
        print(f"superclass got {cls}")
        def _inner(method):
            _name = name if name else method.__name__
            self.commands[_name] = Command(method, _name, cog = self)
