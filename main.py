import time
from datetime import datetime
from slackclient import SlackClient
import redis
import config

class AttributeBot(object):

    def __init__(self, start=True):
        self.last_ping = 0
        if start:
            self.start()

    def connect(self):
        self.client = SlackClient(config.slack_api_token)
        if not self.client.rtm_connect():
            return False

        self.server = self.client.server
        self.uid = self.server.login_data["self"]["id"]
        self.set_home_channel()

    def loop(self):
        now = int(time.time())
        if now > self.last_ping + 3:
            self.server.ping()
            self.last_ping = now

    def start(self):
        self.connect()
        while True:
            for reply in self.client.rtm_read():
                self.process_rtm_reply(reply)

            self.loop()
            time.sleep(0.2)

    def set_home_channel(self, channel_name=config.home_channel):
        c = next(channel.id for channel in self.server.channels
                            if channel.name == channel_name)
        if c:
            self.home_channel = c

    # A message can be directed at the bot in one of three ways:
    # Any message in the home channel.
    # Any direct message to the bot.
    # Any message in any channel when the bot is mentioned.
    def directed_at_bot(self, reply):
        if reply["channel"] == self.home_channel:
            return True

        if reply["channel"].startswith("D"):
            return True

        if reply["text"].find("<@{}>".format(self.uid)) != -1:
            return True

        return False

    def process(self, reply):
        date = datetime.fromtimestamp(float(reply["ts"]))
        print "[{}] [#{}] {}".format(date.strftime("%I:%M%p"), self.server.channels.find(reply["channel"]).name, reply["text"])

    def process_rtm_reply(self, reply):
        if reply["type"] == "message":
            if self.directed_at_bot(reply):
                self.process(reply)

if __name__ == "__main__":
    bot = AttributeBot()
