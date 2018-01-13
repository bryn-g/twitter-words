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

class TweetWords(object):
    SCREEN_NAME_PATTERN = re.compile(r'^@\w{1,15}$', re.UNICODE)
    RETWEET_PATTERN = re.compile(r'^RT\s(@.*?):\s(.*)', re.UNICODE|re.DOTALL)
    WORD_HTTP_PATTERN = re.compile('^https?://', re.UNICODE)
    WORD_STRIP_SPECIAL_PATTERN = re.compile(r'^[^\w@#]+|\W+$', re.UNICODE)

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

    @classmethod
    def is_screen_name(cls, word):
        if cls.SCREEN_NAME_PATTERN.match(word):
            return True
        return False

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

            # don't count empty strings returned by split
            if not word:
                continue

            if not self.WORD_HTTP_PATTERN.match(word):
                # not sure about this - doesnt start with alpha,@,# or doesn't end with alpha
                # removes parenthesis and quotes etc - aggressive / nltk handles now mostly
                word = self.WORD_STRIP_SPECIAL_PATTERN.sub('', word)

                if not word:
                    continue

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

def valid_twitter_user(user_id):
    user_id = str(user_id)

    user_id_match = re.match(r'^@(\w{1,15})$', user_id)

    if user_id_match or user_id.isdigit():
        return user_id
    else:
        msg = "must start with @, be alphanumeric and < 16 characters or be a numeric id."
        raise argparse.ArgumentTypeError(msg)

def insert_newlines(input_string, line_length):
    lines = []
    for i in range(0, len(input_string), line_length):
        lines.append(input_string[i:i+line_length])

    output_string = '\n'.join(lines)
    output_string = re.sub(r'\r?\n\s', r'\n', output_string, re.DOTALL|re.UNICODE)

    return output_string

def print_json(json_block, sort=True, indents=4):
    if type(json_block) is str:
        print(json.dumps(json.loads(json_block), sort_keys=sort, indent=indents))
    else:
        print(json.dumps(json_block, sort_keys=sort, indent=indents))

    return None

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
    parser.add_argument('-u', '--user', help="twitter user @name", type=valid_twitter_user, required=True)
    parser.add_argument('-c', '--count', help="get count number of tweets", type=int, default=1)
    parser.add_argument('-s', '--show', help="show count tweets ", required=False, default=False, action='store_true')
    parser.add_argument('-l', '--min_length', help="min word length", type=int, default=1)
    parser.add_argument('-f', '--min_freq', help="min word frequency", type=int, default=1)
    parser.add_argument('-t', '--top', help="display top number of words by freq", type=int, default=0)
    parser.add_argument('-wc', '--wordcloud', help="create word cloud", required=False, default=False, action='store_true')
    args = parser.parse_args()

    return args

def create_wordcloud(words):
    current_directory = os.path.dirname(__file__)

    word_cloud = wordcloud.WordCloud(
        background_color='white',
        width=1280,
        height=800,
        stopwords=None)

    word_cloud.generate_from_frequencies(words)

    word_cloud.to_file(os.path.join(current_directory, 'wordcloud.png'))

def main():
    twitter_api_keys = get_twitter_env_api_keys()
    tweepy_auth = get_tweepy_auth_handler(twitter_api_keys)

    api = tweepy.API(tweepy_auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True)

    user_args = get_arguments()

    # print(f"type: {type(user_args)} - {user_args}")
    # exit()

    tweet_words = TweetWords(min_word_length=user_args.min_length, min_word_frequency=user_args.min_freq,
                             display_top=user_args.top)

    try:
        timeline_statuses = tweepy.Cursor(api.user_timeline, screen_name=user_args.user, count=user_args.count,
                                          include_rts=True, cursor=-1, tweet_mode='extended').items(user_args.count)

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

            # if tweet_counter == 54:
            #     print_json(tweet._json)

            tweet_created = tweet.created_at

            tweet_text = ""
            if hasattr(tweet, 'full_text'):
                tweet_text = tweet.full_text
            else:
                tweet_text = tweet.text

            if hasattr(tweet, 'entities'):
                if 'urls' in tweet.entities:
                    for u in tweet.entities['urls']:
                        tweet_words.urls[u.get('expanded_url')] += 1

            if hasattr(tweet, 'extended_entities'):
                if 'media' in tweet.extended_entities:
                    for m in tweet.extended_entities['media']:
                        tweet_words.media[m.get('media_url_https')] += 1

            tweet_text = tweet_text.replace("&amp;", "&")

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

            tweet_text = insert_newlines(tweet_text, 65)
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

        if user_args.wordcloud:
            create_wordcloud(tweet_words.get_filtered_words())

    if tweet_words.retweets:
        print("\nRETWEETED")
        tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.retweets), False)

    if tweet_words.replies:
        print("\nREPLIES")
        tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.replies), False)

    if tweet_words.mentions:
        print("\nMENTIONS")
        tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.mentions), False)

    if tweet_words.hashtags:
        print("\nHASHTAGS")
        tweet_words.print_items(tweet_words.get_sorted_items(tweet_words.hashtags), False)

    # print("\nMEDIA")
    # tweet_words.print_items(tweet_words.media, False)
    # print("\nURLS")
    # tweet_words.print_items(tweet_words.urls, False)

if __name__ == '__main__':
    main()
