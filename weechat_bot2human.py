# -*- coding:utf-8 -*-
# Bot2Human
#
# Replaces messages from bots to humans
# typically used in channels that are connected with other IMs using bots
#
# For example, if a bot send messages from XMPP is like `[nick] content`,
# weechat would show `bot | [nick] content` which looks bad; this script
# make weecaht display `nick | content` so that the messages looks like
# normal IRC message
#
# Options
#
#   plugins.var.python.bot2human.bot_nicks
#       space seperated nicknames to forwarding bots
#       example: teleboto toxsync tg2arch
#
#   plugins.var.python.nick_content_re.X
#       X is a 0-2 number. This options specifies regex to match nickname
#       and content. Default regexes are r'\[(?P<nick>.+?)\] (?P<text>.*)',
#       r'\((?P<nick>.+?)\) (?P<text>.*)', and r'<(?P<nick>.+?)> (?P<text>.*)'
#
#   plugins.var.python.nick_re_count
#       Number of rules defined
#

# Changelog:
# 0.2.2: Support ZNC timestamp
# 0.2.1: Color filtering only applies on nicknames
#        More than 3 nick rules can be defined
# 0.2.0: Filter mIRC color and other control seq from message
# 0.1.1: Bug Fixes
# 0.1: Initial Release
#

import weechat as w
import re

SCRIPT_NAME = "bot2human"
SCRIPT_AUTHOR = "Justin Wong & Hexchain"
SCRIPT_DESC = "Replace IRC message nicknames with regex match from chat text"
SCRIPT_VERSION = "0.2.2"
SCRIPT_LICENSE = "GPLv3"

DEFAULTS = {
    'nick_re_count': '4',
    'nick_content_re.0': r'\[(?P<nick>[^:]+?)\] (?P<text>.*)',
    'nick_content_re.1': r'(\x03[0-9,]+)?\[(?P<nick>[^:]+?)\]\x0f? (?P<text>.*)',
    'nick_content_re.2': r'\((?P<nick>[^:]+?)\) (?P<text>.*)',
    'nick_content_re.3': r'<(?P<nick>[^:]+?)> (?P<text>.*)',
    'bot_nicks': "",
    'znc_ts_re': r'\[\d\d:\d\d:\d\d\]\s+',
}

CONFIG = {
    'nick_re_count': -1,
    'nick_content_res': [],
    'bot_nicks': [],
    'znc_ts_re': None,
}


def parse_config():

    for option, default in DEFAULTS.items():
        # print(option, w.config_get_plugin(option))
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default)

    CONFIG['nick_re_count'] = int(w.config_get_plugin('nick_re_count'))
    CONFIG['bot_nicks'] = w.config_get_plugin('bot_nicks').split(' ')
    for i in range(CONFIG['nick_re_count']):
        option = "nick_content_re.{}".format(i)
        CONFIG['nick_content_res'].append(
            re.compile(w.config_get_plugin(option))
        )
    CONFIG['znc_ts_re'] = re.compile(w.config_get_plugin('znc_ts_re'))


def config_cb(data, option, value):
    parse_config()

    return w.WEECHAT_RC_OK


def filter_color(msg):
    # filter \x01 - \x19 control seq
    # filter \x03{foreground}[,{background}] color string
    def char_iter(msg):
        state = "char"
        for x in msg:
            if state == "char":
                if x == '\x03':
                    state = "color"
                    continue
                if 0 < ord(x) <= 0x1f:
                    continue
                yield x
            elif state == "color":
                if '0' < x < '9':
                    continue
                elif x == ',':
                    continue
                else:
                    state = 'char'
                    yield x

    return ''.join(char_iter(msg))


def msg_cb(data, modifier, modifier_data, string):
    # w.prnt("blue", "test_msg_cb " + string)
    parsed = w.info_get_hashtable("irc_message_parse", {'message': string})
    # w.prnt("", "%s" % parsed)

    matched = False
    for bot in CONFIG['bot_nicks']:
        # w.prnt("", "%s, %s" % (parsed["nick"], bot))
        if parsed['nick'] == bot:
            t = parsed.get(
                'text',
                parsed["arguments"][len(parsed["channel"])+2:]
            )
            # ZNC timestamp
            ts = ""
            mts = CONFIG['znc_ts_re'].match(t)
            if mts:
                ts = mts.group()
                t = t[mts.end():]

            for r in CONFIG['nick_content_res']:
                # parsed['text'] only exists in weechat version >= 1.3
                m = r.match(t)
                if not m:
                    continue
                nick, text = m.group('nick'), m.group('text')
                nick = filter_color(nick)
                nick = re.sub(r'\s', '_', nick)
                parsed['host'] = parsed['host'].replace(bot, nick)
                parsed['text'] = ts + text
                matched = True
                break
            if matched:
                break
    else:
        return string

    return ":{host} {command} {channel} :{text}".format(**parsed)


if __name__ == '__main__':
    w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
               SCRIPT_DESC, "", "")

    parse_config()

    w.hook_modifier("irc_in_privmsg", "msg_cb", "")
    w.hook_config("plugins.var.python."+SCRIPT_NAME+".*", "config_cb", "")

# vim: ts=4 sw=4 sts=4 expandtab
