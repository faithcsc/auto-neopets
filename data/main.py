import os
import sys
import json
import random
import logging
import neo
import trudy
import ghoul

logging.basicConfig(
    format=
    "%(asctime)s.%(msecs)03d %(levelname)-5s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO)

# Retrieve account data
NEOPETS_USERNAME = os.environ["NEO_USER"]
USER_CONFIG_FILE = "../conf/secret-neopets"
with open(USER_CONFIG_FILE) as f:
    config = json.loads(f.read())
NEOPETS_PASSWORD = config[NEOPETS_USERNAME]["password"]
enabled_user_tasks = config[NEOPETS_USERNAME]["tasks"]

# # Skip this username with 15% probability
# RANDOM_SKIP_PROBABILITY = 0.15
# if random.random() > (1 - RANDOM_SKIP_PROBABILITY):
#     logging.info("%s Randomly skipping", NEOPETS_USERNAME)
#     exit()


# Login
account = neo.Neo(NEOPETS_USERNAME, NEOPETS_PASSWORD)
usernames = list(config.keys())
progress = usernames.index(NEOPETS_USERNAME) + 1

tasks_to_run = [trudy.Trudy(account), ghoul.GhoulCatchers(account)]

isLoggedIn = account.doLogin()

if not isLoggedIn:
    logging.info("%s Not logged in, skipping this username", NEOPETS_USERNAME)
    sys.exit()

logging.info("%s Enabled user tasks: %s", NEOPETS_USERNAME,
             " ".join(enabled_user_tasks))
for task in tasks_to_run:
    if task.taskName in enabled_user_tasks:
        logging.info("%s %s Starting", NEOPETS_USERNAME, task.taskName)
        task.run()
        account.depositAllNp()

account.cleanUserConfig()
