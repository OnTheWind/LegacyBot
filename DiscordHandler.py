import discord


class DiscordHandler(discord.Client):
    def __init__(self, queue, channel):
        self.output = queue
        self.channel = channel
        discord.Client.__init__(self)

    async def on_ready(self):
        print("The bot is ready!")
        await self.change_presence(game=discord.Game(name="Streaming Users"))

    async def on_message(self, message):
        if message.author == self.user:
            return
        payload = message.content.split(' ')
        command = payload.pop(0)

        if command == Command.ADD:
            discord_id = payload.pop(0)
            twitch_id = payload.pop(0)
            self.output.put({Param.COMMAND: Command.ADD, Param.USER: discord_id, Param.TWITCH: twitch_id})
            await self.write('{} added to streamers'.format(discord_id), message.channel)

        if command == Command.REMOVE:
            discord_id = payload.pop(0)
            self.output.put({Param.COMMAND: Command.REMOVE, Param.USER: discord_id})
            await self.write('{} removed from streamers'.format(discord_id), message.channel)

        if command == Command.LIST:
            self.output.put({Param.COMMAND: Command.LIST, Param.CHANNEL: message.channel})

        if command == Command.SET_CHANNEL:
            self.channel = message.channel
            self.output.put({Param.COMMAND: Command.SET_CHANNEL, Param.CHANNEL: message.channel})
            await self.write('{} set for notification feed'.format(message.channel), message.channel)

    async def write(self, message, channel=''):
        if channel == '':
            channel = self.channel
        await self.send_message(channel, message)


class Command:
    ADD = '!add'
    REMOVE = '!remove'
    LIST = '!list'
    SET_CHANNEL = '!setchannel'
    HELP = '!help'


class Param:
    COMMAND = 'command'
    CHANNEL = 'channel'
    USER = 'user'
    TWITCH = 'twitch'
    MESSAGE = 'message'


class Action:
    WRITE = 'write'
    UPDATE_ROLE = 'update_role'
