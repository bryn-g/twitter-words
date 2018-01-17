import os
import sys
import argparse
import tweepy
import re
import json
import nltk
import wordcloud
import collections
import prettytable
import textblob
import numpy
import PIL
import matplotlib

import twitter_helper

class TweetWords(twitter_helper.TwitterHelper):
    def __init__(self, min_word_length, min_word_frequency, display_top):
        self.words = collections.Counter()
        self.min_word_length = min_word_length
        self.min_word_frequency = min_word_frequency
        self.display_top = display_top

        self.include_retweet_words = False

        self.retweets = collections.Counter()
        self.replies = collections.Counter()
        self.mentions = collections.Counter()
        self.hashtags = collections.Counter()
        self.media = collections.Counter()
        self.urls = collections.Counter()

        self.tweet_tokenizer = nltk.tokenize.TweetTokenizer()

    @staticmethod
    def _get_attr_padding(list_items):
        pad_to = 0
        for item in list_items:
            if type(list_items) is list:
                attr = item[0]
            elif type(list_items) is collections.Counter:
                attr = item
            else:
                print(f"padding type error: {type(list_items)}")
                return pad_to

            if len(attr) > pad_to:
                pad_to = len(attr)

        return pad_to + 1

    @staticmethod
    def get_sorted_items(item_counter, reverse_sort=True):
        return sorted(item_counter.items(), key=lambda pair: pair[1], reverse=reverse_sort)

    # trying out filtering using sort to get top words and then back to counter object so
    # word cloud can use
    def get_filtered_words(self):
        filtered = collections.Counter()
        if self.words:
            for item in self.words:
                attr = item
                value = self.words[item]
                if len(attr) >= self.min_word_length and value >= self.min_word_frequency \
                    and attr not in wordcloud.STOPWORDS:

                    filtered[attr] = value

        # gets a sorted list of tuples
        filtered_sort = self.get_sorted_items(filtered)

        final_list = collections.Counter()
        i = 0
        for item in filtered_sort:
            attr, value = item

            if self.display_top == 0:
                final_list[attr] = value
            else:
                if i < self.display_top:
                    final_list[attr] = value
                    i += 1
                else:
                    break

        return final_list

    def print_items(self, list_items, words=False):
        if not list_items:
            print("none.")
        else:
            i = 0
            pad_to = self._get_attr_padding(list_items)

            for item in list_items:
                if type(list_items) is list:
                    attr, value = item
                elif type(list_items) is collections.Counter:
                    attr = item
                    value = list_items[attr]
                else:
                    print(f"type error: {type(list_items)}")
                    return

                if words:
                    if len(attr) >= self.min_word_length and value >= self.min_word_frequency:
                        if i < self.display_top or self.display_top == 0:
                            print("{0:<{1}s}{2}".format(attr, pad_to, value))
                            i += 1
                else:
                    print("{0:<{1}s}{2}".format(attr, pad_to, value))

    def count_words(self, tweet):
        # retweets - don't count string but count @name as a mention
        retweet_match = self.RETWEET_PATTERN.match(tweet)

        if retweet_match:
            retweet_user = retweet_match.group(1).lower().strip()
            if self.is_screen_name(retweet_user):
                self.retweets[retweet_user] += 1

            # don't process retweets any further
            if self.include_retweet_words:
                tweet = retweet_match.group(2)
            else:
                return

        word_array = self.tweet_tokenizer.tokenize(tweet)

        i = 0
        for word in word_array:
            word = word.lower().strip()

            # don't count empty strings
            if not word:
                continue

            if not self.WORD_HTTP_PATTERN.match(word):
                # not sure about this - doesnt start with alpha,@,# or doesn't end with alpha
                # removes parenthesis and quotes etc - aggressive / nltk handles now mostly
                # word = self.WORD_STRIP_SPECIAL_PATTERN.sub('', word)
                #
                # if not word:
                #     continue

                # hashtags and mentions else words
                if word[0] == "#" and len(word)>1:
                    self.hashtags[word] += 1
                elif self.is_screen_name(word):
                    if i != 0:
                        self.mentions[word] += 1
                else:
                    if word not in wordcloud.STOPWORDS:
                        self.words[word] += 1

            i += 1

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help="twitter user @name", type=twitter_helper.TwitterHelper.arg_twitter_id, required=True)
    parser.add_argument('-c', '--count', help="get count number of tweets", type=int, default=1)
    parser.add_argument('-rt', '--retweets', help="include retweets ", required=False, default=False, action='store_true')
    parser.add_argument('-s', '--show', help="show count tweets ", required=False, default=False, action='store_true')
    parser.add_argument('-l', '--min_length', help="min word length", type=int, default=1)
    parser.add_argument('-f', '--min_freq', help="min word frequency", type=int, default=1)
    parser.add_argument('-t', '--top', help="display top number of words by freq", type=int, default=0)
    parser.add_argument('-wc', '--wordcloud', help="create word cloud", required=False, default=False, action='store_true')
    args = parser.parse_args()

    return args

def create_wordcloud(words):
    current_directory = os.path.dirname(__file__)

    stopwords = set(wordcloud.STOPWORDS)

    word_cloud = wordcloud.WordCloud(
        background_color='white',
        width=1280,
        height=800,
        stopwords=stopwords)

    word_cloud.generate_from_frequencies(words)
    word_cloud.to_file(os.path.join(current_directory, 'wordcloud.png'))

def main():
    twitter_api_keys = twitter_helper.get_twitter_env_api_keys()
    tweepy_auth = twitter_helper.get_tweepy_auth_handler(twitter_api_keys)

    api = tweepy.API(tweepy_auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True)

    user_args = get_arguments()

    # print(f"type: {type(user_args)} - {user_args}")
    # sys.exit()

    tweet_words = TweetWords(min_word_length=user_args.min_length, min_word_frequency=user_args.min_freq,
                             display_top=user_args.top)

    try:
        timeline_statuses = tweepy.Cursor(api.user_timeline, screen_name=user_args.user, count=user_args.count,
                                          include_rts=user_args.retweets, cursor=-1,
                                          tweet_mode='extended').items(user_args.count)

        tweets_table = prettytable.PrettyTable(['', 'Created', 'Reply', 'RT', 'Text', 'Sentiment'])
        tweets_table.align = "l"
        tweets_table.hrules = True

        tweet_counter = 0
        while True:
            try:
                tweet = next(timeline_statuses)
            except tweepy.TweepError as err:
                print(err)
                break
            except StopIteration:
                break

            tweet_counter += 1

            tweet_created = tweet.created_at

            tweet_text = ""
            if hasattr(tweet, 'full_text'):
                tweet_text = tweet.full_text
            else:
                tweet_text = tweet.text

            tweet_text = tweet_text.replace("&amp;", "&")

            if hasattr(tweet, 'entities'):
                if 'urls' in tweet.entities:
                    for u in tweet.entities['urls']:
                        tweet_words.urls[u.get('expanded_url')] += 1

            if hasattr(tweet, 'extended_entities'):
                if 'media' in tweet.extended_entities:
                    for m in tweet.extended_entities['media']:
                        tweet_words.media[m.get('media_url_https')] += 1

            # do all the word things
            tweet_words.count_words(tweet_text)

            tweet_reply_name = ""
            if tweet.in_reply_to_screen_name:
                tweet_reply_name = "@" + tweet.in_reply_to_screen_name
                tweet_words.replies[tweet_reply_name.lower()] += 1

            retweet_name = ""
            retweet_match = tweet_words.RETWEET_PATTERN.match(tweet_text)
            if retweet_match:
                retweet_name = retweet_match.group(1)

            feelings = textblob.TextBlob(tweet_text)
            sentiment = f"pol:{feelings.sentiment[0]:.2f}\nsub:{feelings.sentiment[1]:.2f}"

            tweet_text = twitter_helper.insert_newlines(tweet_text, 65)
            tweets_table.add_row([tweet_counter, tweet_created, tweet_reply_name, retweet_name, tweet_text, sentiment])
    except tweepy.TweepError as err:
        print(f"error: {err}")

    if tweets_table and user_args.show:
        print("TWEETS")
        print(tweets_table)
        print()

    if tweet_words.words:
        print("WORDS")
        tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.words), True)

    # if tweet_words.retweets:
    #     print("\nRETWEETED")
    #     tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.retweets), False)
    #
    # if tweet_words.replies:
    #     print("\nREPLIES")
    #     tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.replies), False)
    #
    # if tweet_words.mentions:
    #     print("\nMENTIONS")
    #     tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.mentions), False)
    #
    if tweet_words.hashtags:
        print("\nHASHTAGS")
        tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.hashtags), False)

    # print("\nMEDIA")
    # tweet_words.print_items(tweet_words.media, False)
    # print("\nURLS")
    # tweet_words.print_items(tweet_words.urls, False)

    if user_args.wordcloud:
        create_wordcloud(tweet_words.get_filtered_words())

if __name__ == '__main__':
    main()
