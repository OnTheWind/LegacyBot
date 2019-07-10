import http.client
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


class TwitchHandler(HTTPServer):
    def __init__(self, server, ip, queue, client_id, secret):
        # Create reference to output queue
        self.output = queue

        # Set up http connection for basic twitch requests
        self.connection = http.client.HTTPSConnection('api.twitch.tv')
        self.ip = ip

        # Twitch API information
        self.client_id = client_id
        self.auth = {'Client-ID': self.client_id}
        self.secret = secret

        super().__init__(server, WebHandler)

    def get_twitch_user_by_name(self, username):
        req = '/helix/users?login=' + username
        self.connection.request('GET', req, None, headers=self.auth)
        response = self.connection.getresponse()
        print('Get twitch id:', response.status, response.reason)
        re = response.read().decode()
        j = json.loads(re)
        print(j)
        return j["data"][0]

    def get_twitch_id(self, username):
        j = self.get_twitch_user_by_name(username)
        return j["id"]

    def subscribe_to_stream(self, username):
        headers = {'Client-ID': self.client_id,
                   'Content-type': 'application/json'}
        subscribe_json = self.build_subscription(username)

        self.connection.request('POST', '/helix/webhooks/hub', body=subscribe_json, headers=headers)
        response = self.connection.getresponse()
        print('Subscribe:', response.status, response.reason)

    def build_subscription(self, username):
        twitch_id = self.get_twitch_id(username)

        json_content = {'hub.callback': self.ip + '/' + username,
                        'hub.mode': 'subscribe',
                        'hub.topic': 'https://api.twitch.tv/helix/streams?user_id=' + twitch_id,
                        'hub.lease_seconds': 600,
                        'hub.secret': self.secret
                        }
        return json.dumps(json_content)


class WebHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        print(self.path)
        url = urlparse(self.path)
        twitch_user = url.path[1:]  # trim leading /
        query = url.query

        try:
            query_data = parse_qs(query)
            challenge = query_data['hub.challenge']
        except:
            return

        if challenge:
            self.server.output.put({Param.COMMAND: Command.UPDATE_EXPIRATION,
                                    Param.TWITCH_USER: twitch_user,
                                    Param.DATETIME: datetime.today() + timedelta(0, Const.LEASE_SECONDS)})
            print('responded to challenge')
            self._set_headers()
            self.wfile.write(bytes(challenge[0], 'utf-8'))

    def do_POST(self):
        # self.server.messages.put('post passed')
        twitch_user = urlparse(self.path).path[1:]
        print(twitch_user)
        data_string = self.rfile.read(int(self.headers['content-length'])).decode('utf-8')
        stream_json = json.loads(data_string)['data'][0]
        print('{}'.format(stream_json))

        self._set_headers()

        if stream_json['type'] != 'live' or stream_json['game'] != Const.MAGIC:
            self.server.output({Param.COMMAND: Command.USER_OFFLINE,
                                Param.TWITCH_USER: twitch_user})
        else:
            self.server.output({Param.COMMAND: Command.USER_ONLINE,
                                Param.TWITCH_USER: twitch_user,
                                Param.TITLE: stream_json['title']})


class Command:
    USER_ONLINE = 'online'
    USER_OFFLINE = 'offline'
    UPDATE_EXPIRATION = 'expiration'

class Param:
    COMMAND = 'command'
    DATETIME = 'datetime'
    TWITCH_USER = 'twitch_user'
    TITLE = 'stream_title'


class Action:
    SUBSCRIBE = 'subscribe'
    LOOKUP = 'lookup'


class Const:
    ID = 'id'
    GAME = 'game_id'
    USER = 'user_name'
    USER_ID = 'user_id'
    TYPE = 'type'
    LEASE_SECONDS = 600
    MAGIC = 2748
