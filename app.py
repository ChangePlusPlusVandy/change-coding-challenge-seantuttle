import argparse
import os
import random
import requests

MAX_NUM_ACCOUNTS = 4  # maximum size of the username wordbank
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")  # can place your bearer token here if needed

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--choose", type=int, help="""Specify that user wants to choose 
                                                accounts and how many they want to choose""")

    args = vars(parser.parse_args())  # get command line args in a dict format

    # exit the program if input is not in range, done to keep the program somewhat small
    if args["choose"] is not None and args["choose"] not in range(2, MAX_NUM_ACCOUNTS + 1):
        import sys
        sys.exit(f"Error: number of twitter accounts must be in range [2, {MAX_NUM_ACCOUNTS}]")

    return args


def get_accounts(args):
    # let user input usernames if command line arg was given, else return default
    if args["choose"]:
        account_list = []
        for i in range(args["choose"]):
            # prompt user for account name, reprompt if given empty string
            new_account = input(f"Enter the username for public figure #{i + 1}: ")
            while(not new_account):
                new_account = input("That account is not valid, please enter another: ")
            account_list.append(new_account)
        
        print()
        return account_list
    else:
        return ["kanyewest", "elonmusk"]  # Kanye and Elon are the default case


def account_list_to_string(account_list):
    account_list_string = ""

    # turn account_list into comma separated string of account names
    for i in range(len(account_list) - 1):
        account_list_string += account_list[i] + ", "

    account_list_string += account_list[-1]

    return account_list_string

def game_introduction(account_list):
    introduction = f"""\

                           Welcome to Guess That Tweeter!
You will be given the text of a Tweet and your job is to guess who sent out that Tweet.
You will have the opportunity to quit the game after every round you play.
After you decide to quit, your stats will be displayed so you can see how well you did.

Your Tweeter wordbank is: {account_list_to_string(account_list)}

Fetching Tweets, this may take a minute...
                    """

    print(introduction)

def handle_failed_response(status_code):
    print(f"\nAPI request failed with status code {status_code}")

    import sys
    sys.exit(status_code)  # terminate program


def is_valid_username(user_name):
    for c in user_name:
        if not c.isalnum() and c != "_":
            return False

    return True


def purge_invalid_tweets(tweet_list):
    i = 0
    while i < len(tweet_list):
        tweet = tweet_list[i]
        tweet_text = tweet["text"]
        at_index = tweet_text.find("@")

        # containing string "http" is considered equivalent to containing a link
        # containing an "@" followed by an alphanumeric char is considered a reply/mention
        # a tweet that starts with the string "RT " is considered a retweet
        # all instances of the above cases will be removed from tweet_list
        if "http" in tweet_text:
            tweet_list.pop(i)
        elif at_index >= 0 and tweet_text[at_index + 1] != " ":
            tweet_list.pop(i)
        elif len(tweet_text) >= 3 and tweet_text[0:1].lower() == "rt ":
            tweet_list.pop(i)
        else:
            i += 1


def get_tweets_for_account(account):
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}  # 401 error if this not included
    base_url = f"https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={account}&count=200"

    # make GET request from api, and request fails if the status_code is not 200
    response = requests.request("GET", base_url, headers=headers)
    if(response.status_code != 200):
        handle_failed_response(response.status_code)

    tweet_list = response.json()  # response.json() returns a list

    # max_id used to ensure first tweet of next page is older than last tweet of current page
    max_id = tweet_list[-1]["id"] - 1
    purge_invalid_tweets(tweet_list)  # get rid of mentions, retweets, links

    # repeat api request until either we reach the maximum number that can be returned
    # or until the account has no more tweets to be returned
    while True:
        url = base_url + f"&max_id={max_id}"
        response = requests.request("GET", url, headers=headers)
        if(response.status_code != 200):
            handle_failed_response(response.status_code)

        # get tweets from the current page, and break from loop if page is empty
        curr_page_tweets = response.json()
        if len(curr_page_tweets) == 0:
            break

        max_id = curr_page_tweets[-1]["id"] - 1
        purge_invalid_tweets(curr_page_tweets)

        tweet_list += curr_page_tweets

    return tweet_list


def get_tweets(account_list):
    tweet_dict = {}  # dict that will contain all account/tweet_list pairs

    for account in account_list:
        curr_tweet_list = get_tweets_for_account(account)  # get tweets for current account
        tweet_dict.update({account: curr_tweet_list})

    return tweet_dict


def get_random_tweet(tweet_dict, account_list):
    # get random account from the list of accounts
    account_index = random.randint(0, len(account_list) - 1)
    account = account_list[account_index]

    # get random tweet from the tweet_list of the account that was just chosen
    tweet_list = tweet_dict[account]
    tweet_index = random.randint(0, len(tweet_list) - 1)
    tweet = tweet_list[tweet_index]

    return account_index, account, tweet


def run_game_loop(tweet_dict, account_list):
    # contains player stats such as total correct and num correct for each account
    stats_dict = {"num_total": 0, "num_correct_total": 0}
    for i in range(len(account_list)):
        stats_dict.update([(f"num_account{i}", 0), (f"num_correct_account{i}", 0)])

    # Get random tweet from random account and display it to the user.
    # Have the user guess, and guess must be from the given Tweet wordbank.
    # Tell user if they were correct or not and record relevant stats
    # Ask the user if they would like to play another round or quit
    while True:
        account_index, account, tweet = get_random_tweet(tweet_dict, account_list)

        # increment total num tweets and num tweets for randomly chosen account
        stats_dict[f"num_account{account_index}"] += 1
        stats_dict["num_total"] += 1

        # show user the random tweet and prompt them for guess, assure it's in wordbank
        print("Here is the tweet:", tweet["text"], sep="\n", end="\n\n")
        account_guess = input("Who do you think tweeted this? ")
        while account_guess not in account_list:
            account_guess = input(f'"{account_guess}" is not an option, guess again: ')

        if account_guess == account:
            stats_dict[f"num_correct_account{account_index}"] += 1
            stats_dict["num_correct_total"] += 1

            print(f"You're correct!")
        else:
            print(f"Not quite! That tweet was by {account}.")

        # ask userif they want to continue, anything but "y" or "Y" means quit
        should_continue = input("Do you want to play another round (y/n)? ")
        print()  # just for spacing purposes
        if should_continue.lower() != "y":
            break

    return stats_dict


def display_stats(stats_dict, account_list):
    print("GAME STATISTICS")

    # print stats for overall performance, then for each individual account
    dividend = stats_dict["num_correct_total"]
    divisor = stats_dict["num_total"]
    perc = dividend / divisor
    print(f"total correct % = {dividend} / {divisor} = {round(100 * perc, 4)}%")

    for i in range(len(account_list)):
        # if an account had tweets featured print the stats; else, print N/A
        if stats_dict[f"num_account{i}"]:
            dividend = stats_dict[f"num_correct_account{i}"]
            divisor = stats_dict[f"num_account{i}"]
            perc = dividend / divisor
            print(f"{account_list[i]} correct % = {dividend} / {divisor} = {round(100 * perc, 4)}%")
        else:
            print(f"{account_list[i]} correct % = N/A")


if __name__ == "__main__":
    args = parse_arguments()  # parse command line arguments

    account_list = get_accounts(args)  # get the usernames for the twitter accounts
    
    game_introduction(account_list)  # print the rules of the game

    tweet_dict = get_tweets(account_list)  # get tweets from all accounts, put in dict

    stats_dict = run_game_loop(tweet_dict, account_list)  # run tweet guessing game

    display_stats(stats_dict, account_list)  # show user how well they did in the game
