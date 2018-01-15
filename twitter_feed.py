import os
import argparse
import re
import json
import tweepy
import colorama
from colorama import Fore, Back, Style

import twitter_helper

class FeedListener(tweepy.streaming.StreamListener):
    stop_count = 100
    tweet_count = 0

    def on_status(self, status):
        if hasattr(status, 'retweeted_status'):
            if status.retweeted_status:
                return

        self.tweet_count += 1

        text = ""
        if hasattr(status, 'extended_tweet') and status.truncated:
            text = status.extended_tweet['full_text']
        else:
            text = status.text

        line_length = 80
        datetime_string = f"{Fore.WHITE}[{Fore.GREEN}{status.created_at}{Fore.WHITE}]"
        padding_count = 21 #len(datetime_string)
        print(f"{datetime_string}[{Fore.CYAN}@{status.user.screen_name}{Fore.WHITE}]{Style.RESET_ALL} #{self.tweet_count}")
        print(f"{twitter_helper.insert_newlines(text, line_length, padding_count)}")

        if self.tweet_count == self.stop_count:
            exit()

    def on_error(self, status_code):
        #if status_code == 420:
        print(f"{Fore.RED}error: {Fore.WHITE}{status_code}")
        return False

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keyword', help="track tweets", type=str, required=True)
    args = parser.parse_args()

    return args

def main():
    colorama.init(autoreset=True)

    twitter_api_keys = twitter_helper.get_twitter_env_api_keys()
    tweepy_auth = twitter_helper.get_tweepy_auth_handler(twitter_api_keys)

    user_args = get_arguments()
    keyword_list = user_args.keyword.split(',')

    twitter_stream = tweepy.Stream(tweepy_auth, FeedListener())
    twitter_stream.filter(track=keyword_list)

if __name__ == '__main__':
    main()
