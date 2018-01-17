import sys
import os
import argparse
import re
import json
import html
import textwrap
import tweepy

import twitter_helper
import text_colorizer

class FeedListener(tweepy.streaming.StreamListener):
    stop_count = 10
    tweet_count = 0

    term = text_colorizer.TermTextColorizer()
    term.add_iro("orange", "172")
    term.add_iro("lgreen", "112")
    term.add_iro("lviolet", "140")
    term.add_iro("dull", "246")

    @classmethod
    def handle_urls(cls, urls, text, count, tag="URL"):
        url_list = []
        for url in urls:
            twitter_url = url['url']
            expanded_url = url['expanded_url']
            url_tag = f"[{tag}#{count}]"
            color_tag = f"{cls.term.iro(url_tag, 'dull')}"
            text = text.replace(twitter_url, color_tag)
            url_list.append(f"[{count}]{expanded_url}")
            count += 1

        return url_list, text, count

    def on_status(self, status):
        #if self.tweet_count == 1:
        #    sys.exit()

        if hasattr(status, 'retweeted_status'):
            if status.retweeted_status:
                return

        self.tweet_count += 1

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
                    for hashtag in status.extended_tweet['entities']['hashtags']:
                        tag = f"#{hashtag['text']}"
                        color_tag = f"{self.term.iro(tag, 'orange')}"
                        text = text.replace(tag, color_tag)

        if hasattr(status, 'entities'):
            if 'urls' in status.entities:
                url_list, text, tweet_url_index = self.handle_urls(status.entities['urls'], text, tweet_url_index)
                tweet_url_list += url_list

            if 'hashtags' in status.entities:
                for hashtag in status.entities['hashtags']:
                    tag = f"#{hashtag['text']}"
                    color_tag = f"{self.term.iro(tag, 'orange')}"
                    text = text.replace(tag, color_tag)

            if 'media' in status.entities:
                url_list, text, tweet_url_index = self.handle_urls(status.entities['media'], text, tweet_url_index, tag="MEDIA")
                tweet_url_list += url_list

        text = html.unescape(text)
        text = re.sub('[ ]{2,}', ' ', text)
        nl = self.term.iro(' • ', 'dull')
        text = re.sub('[\n]{1,}', nl, text)

        quote_status = ""
        if hasattr(status, 'is_quote_status'):
            if status.is_quote_status:
                quote_status = "[quote]"

        quote_mentions = ""
        if hasattr(status, 'quoted_status'):
            if 'entities' in status.quoted_status:
                if 'user_mentions' in status.quoted_status['entities']:
                    for user in status.quoted_status['entities']['user_mentions']:
                        quote_mentions += f" @{user['screen_name']}"

        header_string = f"[{self.term.iro(status.created_at, 'lgreen')}]" + \
                        f"[{self.term.iro('@' + status.user.screen_name, 'lviolet')}] {quote_status}{quote_mentions}"

        tweet_string = f"{text}"
        tweet_string = f"{textwrap.dedent(tweet_string).strip()}"

        padding = ' '*21
        width = len(padding) + 90
        print(f"{textwrap.fill(header_string, width=width, subsequent_indent=padding)}")
        print(f"{textwrap.fill(tweet_string, width=width, initial_indent=padding, subsequent_indent=padding)}")

        if tweet_url_list:
            urls = twitter_helper.insert_newlines(tweet_url_list, 90, padding_count=21, padding_first_line=True,
                                                  newline_to_spaces=False)

            color_urls = f"{self.term.iro(urls, 'dull')}"
            print(f"{color_urls}")

        print()
        #twitter_helper.print_json(status._json)

        if self.tweet_count == self.stop_count:
            exit()

    def on_error(self, status_code):
        print(f"error: {status_code}")
        return False

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--keyword', help="track tweets", type=str, required=True)
    args = parser.parse_args()

    return args

def main():
    twitter_api_keys = twitter_helper.get_twitter_env_api_keys()
    tweepy_auth = twitter_helper.get_tweepy_auth_handler(twitter_api_keys)

    user_args = get_arguments()
    keyword_list = user_args.keyword.split(',')

    twitter_stream = tweepy.Stream(tweepy_auth, FeedListener())
    twitter_stream.filter(track=keyword_list)

if __name__ == '__main__':
    main()
