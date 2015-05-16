#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
from datetime import datetime
from slackclient import SlackClient
import redis
import config

class AttributeBot(object):

    def __init__(self, start=True):
        logging.basicConfig(filename=config.log_path, level=getattr(logging, config.log_level.upper()))
        self.r = redis.from_url(config.redis_url)
        self.last_ping = 0
        if start:
            self.start()

    def p(self, s):
        return "{}:{}".format(config.redis_prefix, s)

    def connect(self):
        self.client = SlackClient(config.slack_api_token)
        if not self.client.rtm_connect():
            return False

        self.server = self.client.server
        self.uid = self.server.login_data["self"]["id"]
        self.set_home_cid()

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

    def set_home_cid(self, channel_name=config.home_channel):
        c = next(channel.id for channel in self.server.channels
                            if channel.name == channel_name)
        if c:
            self.home_cid = c

    # A message can be directed at the bot in one of three ways:
    # Any message in the home channel.
    # Any direct message to the bot.
    # Any message in any channel when the bot is mentioned.
    def directed_at_bot(self, reply):
        if reply["channel"] == self.home_cid:
            return True

        if reply["channel"].startswith("D"):
            return True

        if reply.get("text", "").find("<@{}>".format(self.uid)) != -1:
            return True

        return False

    def strip_meta(self, s):
        u = "<@{}>".format(self.uid)
        if s.endswith(u):
            s = s[:-len(u)]

        if s.startswith(u):
            s = s[len(u):]

        if s.startswith(":"):
            s = s[1:]

        return s.strip()


    def log_feeling(self, uid, attribute, time):
        key = self.p("feeling:{}:{}".format(uid, attribute))
        self.r.lpush(key, time)

    def last_feeling(self, uid, attribute):
        key = self.p("feeling:{}:{}".format(uid, attribute))
        date = self.r.lrange(key, 0, 0)
        if len(date) == 0:
            return "You’ve never felt “{}” before.".format(attribute)
        else:
            date = datetime.fromtimestamp(float(date[0]))
            return "You last felt “{}” at {}".format(attribute, date.strftime("%b %-d ’%y %-I:%M %p"))

    def process(self, reply):
        command = self.strip_meta(reply["text"].strip())
        uid = reply["user"]
        date = datetime.fromtimestamp(float(reply["ts"]))

        if command.startswith("last feeling "):
            self.client.rtm_send_message(reply["channel"], self.last_feeling(uid, command[13:]))
        elif command.startswith("feeling "):
            self.log_feeling(uid, command[8:], reply["ts"])

    def process_rtm_reply(self, reply):
        if reply.get("type") == "pong":
            return

        logging.debug(reply)
        if reply.get("type") == "message":
            if reply.get("subtype") == "message_changed":
                reply["text"] = reply["message"]["text"]
                reply["user"] = reply["message"]["user"]

            if self.directed_at_bot(reply):
                self.process(reply)

if __name__ == "__main__":
    bot = AttributeBot()
