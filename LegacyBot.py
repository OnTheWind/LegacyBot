import asyncio
import json
import queue
from datetime import datetime, timedelta
from threading import Thread
from Project import keys

import discord

from Project.DiscordHandler import DiscordHandler, Command as DComm, Param as DParam, Action as DAction
from Project.TwitchHandler import TwitchHandler, Command as TComm, Param as TParam, Action as TAction


class LegacyBot(discord.Client):
    def __init__(self):

        self.config = Config()
        self.config.load()
        self.users = {}

        # Start queues
        self.discord_queue = queue.Queue()
        self.twitch_queue = queue.Queue()

        # Initialize Handlers
        self.discord_handler = DiscordHandler(queue=self.discord_queue,
                                              channel=self.config.channel)

        self.twitch_handler = TwitchHandler(server=('', 8000),
                                            ip=self.config.ip,
                                            queue=self.twitch_queue,
                                            client_id=self.config.twitch_client_id,
                                            secret=self.config.twitch_secret)

        self.twitch_action(TAction.SUBSCRIBE, user='on_the_wind')

        discord.Client.__init__(self)

    def start_handlers(self):
        Thread(target=self.twitch_handler.serve_forever()).start()
        Thread(target=self.discord_handler.run(self.config.discord_key)).start()

    def loop(self):
        while True:
            empty = self.check_discord_queue()
            empty += self.check_twitch_queue()
            if empty:
                asyncio.sleep(5)

    def check_discord_queue(self):
        request = self.discord_queue.get()
        command = request[DParam.COMMAND]
        if command is None:
            return True
        if command == DComm.SET_CHANNEL:
            self.config.channel = request[DParam.CHANNEL]
            print('update channel')
            # TODO save config
        elif command == DComm.ADD:
            discord_id = request[DParam.USER]
            twitch_user = request[DParam.TWITCH]
            twitch_json = self.twitch_action(TAction.LOOKUP, user=twitch_user)
            self.add_user(discord_id, twitch_user, twitch_json['id'])
            # subscribe if user expires in less than 60 seconds
            if self.users.get(twitch_user).expiration < datetime.now() + timedelta(0, 60):
                self.twitch_action(TAction.SUBSCRIBE, user=twitch_user)
            # TODO save user
        elif command == DComm.LIST:
            summary = 'Subscribed Users:'
            summary += '\n' + 'Discord ID:'.ljust(15) + 'Twitch User'.ljust(15) + 'Expiration'
            for twitch_user in self.users:
                discord_id = self.users.get(twitch_user).discord_id
                expiration = self.users.get(twitch_user).expiration
                summary += '\n' + discord_id.ljust(15) + twitch_user.ljust(15) + expiration
        else:
            print('un-implemented discord input:' + command)

    def check_twitch_queue(self):
        request = self.twitch_queue.get()
        command = request[TParam.COMMAND]
        if command is not None:
            print('from twitch:' + command)
        if command == TComm.UPDATE_EXPIRATION:
            twitch_user = request[TParam.TWITCH_USER]
            datetime = request[TParam.DATETIME]
            self.users.get(twitch_user).expiration = datetime
            # TODO save datetime

        elif command == TComm.USER_ONLINE:
            twitch_user = request[TParam.TWITCH_USER]
            stream_title = request[TParam.TITLE]
            message = stream_title + '\n' + twitch_user + 'has gone live'
            self.discord_action(DAction.WRITE, message=message)
            self.discord_action(DAction.UPDATE_ROLE)
            # TODO role update

        elif command == TComm.USER_OFFLINE:
            twitch_user = request[TParam.TWITCH_USER]
            message = twitch_user + 'has gone offline'
            self.discord_action(DAction.WRITE, message=message)
            # TODO role update

    def discord_action(self, command, **kwargs):
        if command == DAction.WRITE:
            self.discord_handler.write(kwargs.get('message'))

        elif command == DAction.UPDATE_ROLE:
            # TODO role update
            return

    def twitch_action(self, command, **kwargs):
        if command == TAction.SUBSCRIBE:
            self.twitch_handler.subscribe_to_stream(kwargs.get('user'))

        if command == TAction.LOOKUP:
            return self.twitch_handler.get_twitch_user_by_name(kwargs.get('user'))

    def add_user(self, discord_id, twitch_user, twitch_id, expiration=0, status=''):
        if self.users.get(twitch_user):
            return False
        self.users[twitch_user] = User(discord_id, twitch_user, twitch_id, expiration, status)
        self.users[twitch_user].save(self.config.user_file)
        return True


class User:
    def __init__(self, discord_id, twitch_user, twitch_id, expiration=0, status=''):
        self.discord_id = discord_id
        self.twitch_user = twitch_user
        self.twitch_id = twitch_id
        self.expiration = expiration
        self.status = status

    def to_json(self):
        return json.dumps({'discord_id': self.discord_id,
                           'twitch_user': self.twitch_user,
                           'twitch_id': self.twitch_id,
                           'expiration': self.expiration})

    def save(self, file):
        # TODO
        return


class Config:
    def __init__(self):
        self.user_file = ''
        self.discord_key = ''
        self.twitch_secret = ''
        self.twitch_client_id = ''
        self.ip = ''
        self.channel = ''

    def load(self):
        keys.load(self)

    def save(self):
        # TODO
        return


legacy_bot = LegacyBot()
legacy_bot.start_handlers()
legacy_bot.loop()
