import os
import sys
import random
sys.path[0] = ""
os.chdir("../data/")

import neo
import trudy
import ghoul
os.chdir("../conf/")

import logging
logging.basicConfig(
    format=
    "%(asctime)s.%(msecs)03d %(levelname)-5s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO)

import json
with open("secret-neopets") as f:
    settings = json.loads(f.read())
    usernames = list(settings.keys())
    random.shuffle(usernames)
    shuffled_settings = {}
    for username in usernames:
        shuffled_settings[username] = settings[username]
    settings = shuffled_settings

write_lines = []
for username, task_values in settings.items():
    account = neo.Neo(task_values.get("username"), task_values.get("password"))

    tasks_to_run = [trudy.Trudy(account), ghoul.GhoulCatchers(account)]
    enabled_user_tasks = task_values.get("tasks", ["trudy", "ghoul"])
    
    runnable_tasks = []
    if account.checkIfShouldLogin():
        for task in tasks_to_run:
            if task.isRunnableTask():
                if task.taskName in enabled_user_tasks:
                    runnable_tasks.append(task.taskName)

    if runnable_tasks:
        logging.info("{} {}".format(username, ", ".join(runnable_tasks)))
        write_lines.append("{}:{}\n".format(username,
                                            settings[username]["city"]))
    else:
        logging.info("{} None".format(username))

from os.path import expanduser
home = expanduser("~")
with open(home + "/username_vpn_region", "w") as f:
    for i, line in enumerate(write_lines):
        f.write("{}/{}:{}".format(i + 1, len(write_lines), line))
