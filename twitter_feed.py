import sys
import os
import argparse
import re
import json
import html
import textwrap
import tweepy
import ssl
import time

import twitter_helper

class FeedListener(tweepy.streaming.StreamListener):
    # tweet padding and line widths in chars
    PADDING_WIDTH = 21
    LINE_WIDTH = 90

    term = twitter_helper.TextColorSet()

    def __init__(self):
         super().__init__()
         self.tweet_count = 0
         self.retweet_count = 0

    @classmethod
    def handle_urls(cls, urls, text, url_index, tag="URL"):
        url_list = []
        for url in urls:
            text = text.replace(url['url'], cls.term.gray(f"[{tag}#{url_index}]"))
            url_list.append(f"[{url_index}]{url['expanded_url']}")
            url_index += 1

        return url_list, text, url_index

    @classmethod
    def handle_hashtags(cls, hashtags, text):
        for hashtag in hashtags:
            text = text.replace(f"#{hashtag['text']}", cls.term.orange(f"#{hashtag['text']}"))

        return text

    @classmethod
    def clean_text(cls, text):
        text = html.unescape(text)
        text = re.sub('[ ]{2,}', ' ', text)
        text = re.sub('[\r\n]{1,}', cls.term.gray(' • '), text)

        return text

    def on_status(self, status):
        self.tweet_count += 1

        if hasattr(status, 'retweeted_status'):
            if status.retweeted_status:
                self.retweet_count += 1
                return

        text = ""
        if hasattr(status, 'extended_tweet') and status.truncated:
            text = status.extended_tweet['full_text']
        else:
            text = status.text

        tweet_url_index = 0 # per tweet
        tweet_url_list = []

        if hasattr(status, 'extended_tweet'):
            if 'entities' in status.extended_tweet:
                if 'urls' in status.extended_tweet['entities']:
                    url_list, text, tweet_url_index = self.handle_urls(status.extended_tweet['entities']['urls'], text, tweet_url_index)
                    tweet_url_list += url_list

                if 'hashtags' in status.extended_tweet['entities']:
                    text = self.handle_hashtags(status.extended_tweet['entities']['hashtags'], text)

        if hasattr(status, 'entities'):
            if 'urls' in status.entities:
                url_list, text, tweet_url_index = self.handle_urls(status.entities['urls'], text, tweet_url_index)
                tweet_url_list += url_list

            if 'hashtags' in status.entities:
                text = self.handle_hashtags(status.entities['hashtags'], text)

            if 'media' in status.entities:
                url_list, text, tweet_url_index = self.handle_urls(status.entities['media'], text, tweet_url_index, tag="MEDIA")
                tweet_url_list += url_list

        # tweet quote
        quote_status = ""
        if hasattr(status, 'is_quote_status'):
            if status.is_quote_status:
                quote_status = "[quote]"

        quote_mentions = ""
        if hasattr(status, 'quoted_status'):
            if 'entities' in status.quoted_status:
                if 'user_mentions' in status.quoted_status['entities']:
                    for user in status.quoted_status['entities']['user_mentions']:
                        quote_mentions += f" {self.term.plum('@' + user['screen_name'])}"

        # twitter screen names
        text = re.sub(twitter_helper.TwitterHelper.TWEET_SCREEN_NAME_PATTERN, self.term.gold(r'\1'), text)

        # additional text cleanup
        text = self.clean_text(text)

        # output
        print(f"[tweets: {self.term.darkcyan(self.tweet_count)} retweet: {self.term.darkcyan(self.retweet_count)}]")

        header_string = f"[{self.term.green(status.created_at)}]" + \
                        f"[{self.term.purple('@' + status.user.screen_name)}] {quote_status}{quote_mentions}"

        text = f"{textwrap.dedent(text).strip()}"

        padding = ' '*self.PADDING_WIDTH
        width = self.PADDING_WIDTH + self.LINE_WIDTH
        print(f"{textwrap.fill(header_string, width=width+self.PADDING_WIDTH, subsequent_indent=padding)}")
        print(f"{textwrap.fill(text, width=width, initial_indent=padding, subsequent_indent=padding)}")

        if tweet_url_list:
            urls = twitter_helper.insert_newlines(tweet_url_list, self.LINE_WIDTH, padding_count=self.PADDING_WIDTH,
                                                  padding_first_line=True, newline_to_spaces=False)

            color_urls = f"{self.term.gray(urls)}"
            print(f"{color_urls}")

        print()

    def on_error(self, status):
        if status == 420:
            print(f"{self.term.darkcyan('Stream is limited.')}")
        else:
            print(f"{self.term.darkcyan('Stream error: ' + status)}")

        return False

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keyword', help="track tweets", type=str, required=True)
    args = parser.parse_args()

    return args

def main():
    error_retry = 3;

    term = twitter_helper.TextColorSet()

    twitter_api_keys = twitter_helper.get_twitter_env_api_keys()
    tweepy_auth = twitter_helper.get_tweepy_auth_handler(twitter_api_keys)

    user_args = get_arguments()
    keyword_list = user_args.keyword.split(',')

    twitter_stream = tweepy.Stream(tweepy_auth, FeedListener())

    print(f"{time.ctime()}")
    while (error_retry > 0):
        try:
            twitter_stream.filter(track=keyword_list, async=False)
        except ssl.SSLError:
            print(f"\n{term.darkcyan('Connection timeout. Stopping twitter feed.')}")
            twitter_stream.disconnect()
        except Exception as err:
            twitter_stream.disconnect()
            print(f"\n{term.darkcyan('Error. Stopping twitter feed.')} > {err}")
        except:
            print(f"\n{term.darkcyan('Error. Stopping twitter feed.')}")
            try:
                twitter_stream.disconnect()
            except:
                print(f"{term.darkcyan('Stream disconnect error.')}")

            break

        print(f"{time.ctime()} (retry: {error_retry})")
        error_retry -= 1
        time.sleep(10)

if __name__ == '__main__':
    main()
