import os
import argparse
import re
import json
import tweepy
import colorama
from colorama import Fore, Back, Style

class feed_listener(tweepy.streaming.StreamListener):
    RETWEET_PATTERN = re.compile(r'^RT\s(@.*?):\s(.*)', re.UNICODE|re.DOTALL)
    stop_count = 100
    tweet_count = 0

    @staticmethod
    def insert_newlines(input_string, line_length, spacer):

        input_string = re.sub('\n', ' ', input_string)

        lines = []
        for i in range(0, len(input_string), line_length):
            lines.append(input_string[i:i+line_length])

        spaces = " "*spacer
        output_string = '\n'.join(lines)
        output_string = re.sub('\n', '\n'+spaces, output_string)

        return output_string

    def on_status(self, status):
        if hasattr(status, 'retweeted_status'):
            if status.retweeted_status:
                return

        text = ""
        if hasattr(status, 'extended_tweet') and status.truncated:
            text = status.extended_tweet['full_text']
        else:
            text = status.text

        line_length = 65
        #meta = f"[{status.created_at}][@{status.user.screen_name}]["
        #spacer = len(meta)
        spacer = 21
        print(f"[{Fore.GREEN}{status.created_at}{Fore.WHITE}][{Fore.CYAN}@{status.user.screen_name}{Fore.WHITE}]")
        print(f"{' '*spacer}{Fore.YELLOW}[{Fore.WHITE}{self.insert_newlines(text, line_length, spacer)}{Fore.YELLOW}]")

        self.tweet_count += 1
        if self.tweet_count == self.stop_count:
            exit()

    def on_error(self, status_code):
        if status_code == 420:
            return False

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

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keyword', help="track tweets", type=str, required=True)
    args = parser.parse_args()

    return args

def main():
    colorama.init(autoreset=True)

    twitter_api_keys = get_twitter_env_api_keys()
    tweepy_auth = get_tweepy_auth_handler(twitter_api_keys)

    user_args = get_arguments()
    keyword_list = user_args.keyword.split(',')

    twitter_stream = tweepy.Stream(tweepy_auth, feed_listener())
    twitter_stream.filter(track=keyword_list)

if __name__ == '__main__':
    main()
