from async_property import async_property

class Command:
    def __init__(self, coro, name):
        self.coro = coro
        self.name = name
        self.help = self.coro.__doc__

    async def execute(self, ctx, args):
        return await self.coro(ctx, args)

class Defaults:
    @staticmethod
    async def help(ctx, args):
        _help = ""
        for command in ctx.client.commands:
            _help += f"{command.name} - {command.help if command.help else 'no docstring'}\n"

        await ctx.send(_help)

    @staticmethod
    async def default(ctx, args):
        return
