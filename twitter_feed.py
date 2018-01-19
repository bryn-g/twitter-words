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
import text_colorizer

class FeedListener(tweepy.streaming.StreamListener):
    # tweet padding and line widths in chars
    PADDING_WIDTH = 21
    LINE_WIDTH = 90

    # terminal color assignment
    term = text_colorizer.TermTextColorizer()
    term.add_iro("orange", "172")
    term.add_iro("gold", "220")
    term.add_iro("green", "112")
    term.add_iro("purple", "140")
    term.add_iro("gray", "246")
    term.add_iro("plum", "96")

    @classmethod
    def handle_urls(cls, urls, text, count, tag="URL"):
        url_list = []
        for url in urls:
            twitter_url = url['url']
            expanded_url = url['expanded_url']
            url_tag = f"[{tag}#{count}]"
            color_tag = f"{cls.term.iro(url_tag, 'gray')}"
            text = text.replace(twitter_url, color_tag)
            url_list.append(f"[{count}]{expanded_url}")
            count += 1

        return url_list, text, count

    def on_status(self, status):
        if hasattr(status, 'retweeted_status'):
            if status.retweeted_status:
                return

        text = ""
        if hasattr(status, 'extended_tweet') and status.truncated:
            text = status.extended_tweet['full_text']
        else:
            text = status.text

        tweet_url_index = 0
        tweet_url_list = []

        if hasattr(status, 'extended_tweet'):
            if 'entities' in status.extended_tweet:
                if 'urls' in status.extended_tweet['entities']:
                    url_list, text, tweet_url_index = self.handle_urls(status.extended_tweet['entities']['urls'], text, tweet_url_index)
                    tweet_url_list += url_list

                if 'hashtags' in status.extended_tweet['entities']:
                    if len(status.extended_tweet['entities']['hashtags']) > 6:
                        return

                    for hashtag in status.extended_tweet['entities']['hashtags']:
                        tag = f"#{hashtag['text']}"
                        color_tag = f"{self.term.iro(tag, 'orange')}"
                        text = text.replace(tag, color_tag)

        if hasattr(status, 'entities'):
            if 'urls' in status.entities:
                url_list, text, tweet_url_index = self.handle_urls(status.entities['urls'], text, tweet_url_index)
                tweet_url_list += url_list

            if 'hashtags' in status.entities:
                if len(status.entities['hashtags']) > 6:
                    return

                for hashtag in status.entities['hashtags']:
                    tag = f"#{hashtag['text']}"
                    color_tag = f"{self.term.iro(tag, 'orange')}"
                    text = text.replace(tag, color_tag)

            if 'media' in status.entities:
                url_list, text, tweet_url_index = self.handle_urls(status.entities['media'], text, tweet_url_index, tag="MEDIA")
                tweet_url_list += url_list

        text = html.unescape(text)
        text = re.sub('[ ]{2,}', ' ', text)
        nl = self.term.iro(' • ', 'gray')
        text = re.sub('[\n]{1,}', nl, text)

        # color twitter names in tweet
        text = re.sub(twitter_helper.TwitterHelper.TWEET_SCREEN_NAME_PATTERN, self.term.iro(r'\1', 'gold'), text)

        quote_status = ""
        if hasattr(status, 'is_quote_status'):
            if status.is_quote_status:
                quote_status = "[quote]"

        quote_mentions = ""
        if hasattr(status, 'quoted_status'):
            if 'entities' in status.quoted_status:
                if 'user_mentions' in status.quoted_status['entities']:
                    for user in status.quoted_status['entities']['user_mentions']:
                        quote_mentions += f" {self.term.iro('@' + user['screen_name'], 'plum')}"

        header_string = f"[{self.term.iro(status.created_at, 'green')}]" + \
                        f"[{self.term.iro('@' + status.user.screen_name, 'purple')}] {quote_status}{quote_mentions}"

        tweet_string = f"{text}"
        tweet_string = f"{textwrap.dedent(tweet_string).strip()}"

        padding = ' '*self.PADDING_WIDTH
        width = self.PADDING_WIDTH + self.LINE_WIDTH
        print(f"{textwrap.fill(header_string, width=width+self.PADDING_WIDTH, subsequent_indent=padding)}")
        print(f"{textwrap.fill(tweet_string, width=width, initial_indent=padding, subsequent_indent=padding)}")

        if tweet_url_list:
            urls = twitter_helper.insert_newlines(tweet_url_list, self.LINE_WIDTH, padding_count=self.PADDING_WIDTH,
                                                  padding_first_line=True, newline_to_spaces=False)

            color_urls = f"{self.term.iro(urls, 'gray')}"
            print(f"{color_urls}")

        print()

    def on_error(self, status):
        if status == 420:
            print(f"Stream is limited.")
        else:
            print(f"Stream error: {status}")

        return False

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keyword', help="track tweets", type=str, required=True)
    args = parser.parse_args()

    return args

def main():
    term = text_colorizer.TermTextColorizer()
    term.add_iro("blue", "38")

    twitter_api_keys = twitter_helper.get_twitter_env_api_keys()
    tweepy_auth = twitter_helper.get_tweepy_auth_handler(twitter_api_keys)

    user_args = get_arguments()
    keyword_list = user_args.keyword.split(',')

    twitter_stream = tweepy.Stream(tweepy_auth, FeedListener())

    try:
        twitter_stream.filter(track=keyword_list, async=False)
    except ssl.SSLError:
        print(f"\n{term.iro('Connection timeout. Stopping twitter feed.', 'blue')}")
        twitter_stream.disconnect()
    except:
        print(f"\n{term.iro('Error. Stopping twitter feed.', 'blue')}")
        try:
            twitter_stream.disconnect()
        except:
            print(f"{term.iro('Stream disconnect error.', 'blue')}")

if __name__ == '__main__':
    main()
