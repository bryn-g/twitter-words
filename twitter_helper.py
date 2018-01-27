import os
import re
import argparse
import json
import tweepy

import text_colorizer

class TextColorSet(text_colorizer.TermTextColorizer):
    def __init__(self):
        super().__init__()
        self.add_iro("orange", "172")
        self.add_iro("gold", "220")
        self.add_iro("green", "112")
        self.add_iro("purple", "140")
        self.add_iro("gray", "246")
        self.add_iro("plum", "96")
        self.add_iro("darkcyan", "38")
        self.add_iro("bg_green", "112", True)
        self.add_iro("bg_plum", "96", True)
        self.add_iro("bg_gray", "246", True)

class TwitterHelper(object):
    SCREEN_NAME_PATTERN = re.compile(r'^@?[A-Za-z0-9_]{1,15}$', re.UNICODE)
    TWEET_SCREEN_NAME_PATTERN = re.compile(r'(@[A-Za-z0-9_]{1,15})', re.DOTALL)
    RETWEET_PATTERN = re.compile(r'^RT\s(@.*?):\s(.*)', re.UNICODE|re.DOTALL)
    WORD_HTTP_PATTERN = re.compile('^https?://', re.UNICODE)
    WORD_STRIP_SPECIAL_PATTERN = re.compile(r'^[^\w@#]+|\W+$', re.UNICODE)

    @classmethod
    def is_screen_name(cls, word):
        if cls.SCREEN_NAME_PATTERN.match(word):
            return True
        return False

    @classmethod
    def arg_twitter_id(cls, user_id):
        user_id = str(user_id)

        if cls.SCREEN_NAME_PATTERN.match(user_id) or user_id.isdigit():
            return user_id
        else:
            msg = "must start with @, be alphanumeric and < 16 characters or be a numeric id."
            raise argparse.ArgumentTypeError(msg)

def get_twitter_env_api_keys(consumer_key='TWITTER_CONSUMER_KEY', consumer_secret='TWITTER_CONSUMER_SECRET',
                             access_key='TWITTER_ACCESS_KEY', access_secret='TWITTER_ACCESS_SECRET'):

    api_keys = {}
    api_keys['consumer_key'] = os.environ.get(consumer_key, 'None')
    api_keys['consumer_secret'] = os.environ.get(consumer_secret, 'None')
    api_keys['access_key'] = os.environ.get(access_key, 'None')
    api_keys['access_secret'] = os.environ.get(access_secret, 'None')

    env_missing = False
    for item in api_keys:
        if api_keys[item] is 'None':
            env_missing = True
    if env_missing:
        print("warning: twitter api env variables missing.")

    return api_keys

def get_tweepy_auth_handler(twitter_api_keys):
    auth = tweepy.OAuthHandler(twitter_api_keys['consumer_key'], twitter_api_keys['consumer_secret'])
    auth.set_access_token(twitter_api_keys['access_key'], twitter_api_keys['access_secret'])

    return auth

def print_json(json_block, sort=True, indents=4):
    if type(json_block) is str:
        print(json.dumps(json.loads(json_block), sort_keys=sort, indent=indents))
    else:
        print(json.dumps(json_block, sort_keys=sort, indent=indents))

    return None

def cut_lines(input_string, line_length):
    lines = []
    for i in range(0, len(input_string), line_length):
        lines.append(input_string[i:i+line_length])

    return lines

def insert_newlines(input_text, line_length, padding_count=0, padding_first_line=False, newline_to_spaces=False):
    output_string = ""
    if type(input_text) is list:
        for line in input_text:
            output_string += '\n'
            output_string += '\n'.join(cut_lines(line, line_length))

    elif type(input_string) is str:
        input_string = input_text

        if newline_to_spaces:
            input_string = re.sub('\r?\n', ' ', input_string)

        output_string = '\n'.join(cut_lines(input_string, line_length))
    else:
        return ""

    if padding_count > 0:
        spaces = " "*padding_count
        output_string = re.sub('\n', '\n'+spaces, output_string)
        if padding_first_line:
            output_string = spaces + output_string

    return output_string
