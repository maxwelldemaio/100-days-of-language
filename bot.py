import os, mysql.connector, time, tweepy

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

""" 
Dev NOTE: For testing purposes set the items(limit=3) to only get three tweets and test.
Also the logs will have the most recent tweet ID if needed / can check Twitter web.
"""

# Setup OAuth authentication for Tweepy
auth = tweepy.OAuthHandler(os.getenv("API_KEY"), os.getenv("API_SECRET_KEY"))
auth.set_access_token(os.getenv("ACCESS_TOKEN"), os.getenv("ACCESS_SECRET"))
# Rate limit = True: allows us to wait 15 minutes before retrying request
api = tweepy.API(auth, wait_on_rate_limit=True)

# Setup MySQL db
mydb = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_DB"))
mycursor = mydb.cursor()


# New function for getting the blacklist as a set of strings.
def getBlacklist() -> set:
    mycursor.execute(
        "SELECT twitterUser FROM blacklist)
    myresult = mycursor.fetchall()
    usernames = set([row[0] for row in myresult])
    return usernames
   
        
# New function for getting the supporters as a set of strings.
def getSupporters() -> set:
    mycursor.execute(
        "SELECT twitterUser FROM supporter)
    myresult = mycursor.fetchall()
    usernames = set([row[0] for row in myresult])
    return usernames
        
        
def retrieveLastSeenId() -> int:
    mycursor.execute("SELECT * FROM tweet")
    myresult = mycursor.fetchall()
    return myresult[0][1]


def storeLastSeenId(lastSeenId: int) -> None:
    exampleId: int = (lastSeenId)
    mycursor.execute("UPDATE tweet SET tweetId = '%s' WHERE id = 1", (exampleId,))
    mydb.commit()
    print(mycursor.rowcount, "record(s) affected", flush=True)
    return


def main(myQuery: str) -> None:
    # Obtain last seen tweet
    lastSeenId: int = retrieveLastSeenId()
    print("Last seen tweet: " + str(lastSeenId) + "\n", flush=True)

    # Set up tweets from api
    # Only select tweets from our query and since our last seen tweet
    # Reverse the generator (which is an iterator, all generators are iterators, all iterators are iterables)
    # This makes the tweets ordered from oldest -> newest
    tweets = reversed(list(tweepy.Cursor(api.search, since_id=lastSeenId, q=myQuery).items()))

    # Setup current last seen tweet to be the previous one
    # This is just in case there are no items in the iterator
    currLastSeenId: int = lastSeenId

    # Setup tweeters frequency map for rate limit
    tweeters: dict[str, int] = {}

    # Get blacklist here
    blackList : set = getBlacklist()
        
    # Get supporters here
    supporters : set = getSupporters()
        
    for tweet in tweets:
        try:
            twitterUser: str = tweet.user.screen_name
            
            #Skip if user in blacklist
            if twitterUser in blackList:
                print("Blacklisted tweet by - @" + twitterUser, flush=True)
                continue
        
            # Add to frequency map
            if twitterUser not in tweeters:
                tweeters[twitterUser] = 1
            else:
                tweeters[twitterUser] += 1
        
            # Make sure they have not met rate limit of 2 tweets per 10 minutes
            if tweeters[twitterUser] <= 2:
                # Like tweet if supporter
                if twitterUser in supporters:
                    tweet.favorite()
                    print("Liking tweet by" + twitterUser, flush=True)

                # Retweet post
                print("Retweet Bot found tweet by @" + 
                    twitterUser + ". " + "Attempting to retweet...", flush=True)
                tweet.retweet()
                print(tweet.text, flush=True)
                print("Tweet retweeted!", flush=True)

            # Update last seen tweet with the newest tweet (bottom of list)
            currLastSeenId = tweet.id
            time.sleep(5)

        # Basic error handling - will print out why retweet failed to terminal
        except tweepy.TweepError as e:
            print(e.reason, "Tweet id: " + str(tweet.id), flush=True)
            if e.api_code == 185:
                print("Rate limit met, ending program", flush=True)
                break

        except StopIteration:
            print("Stopping...", flush=True)
            break
    
    # After iteration, store the last seen tweet id (newest)
    # Only store if it is different
    if(lastSeenId != currLastSeenId):
        storeLastSeenId(currLastSeenId)
        print("Updating last seen tweet to: " +
        str(currLastSeenId) + "\n", flush=True)

    return



if __name__ == "__main__":
    main("#langtwt OR #100DaysOfLanguage OR 100daysoflanguage -filter:retweets -result_type:recent")
    mycursor.close()
    mydb.close()
    print("\nRetweet function completed and db connection closed", flush=True)
