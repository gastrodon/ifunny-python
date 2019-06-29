def _default(ctx, args):
    return

def _help(ctx, args):
    """
    List commands
    """
    _help = ""
    for command in ctx.client.commands:
        command = ctx.client.commands[command]
        _help += f"{command.name} - {command.help if command.help else 'no docstring'}\n"

    ctx.send(_help)

class Command:
    def __init__(self, method, name):
        self.method = method
        self.name = name
        self.help = self.method.__doc__

    def execute(self, ctx, args):
        return self.method(ctx, args)

class Defaults:

    help = Command(_help, "help")

    default = Command(_default, "default")
