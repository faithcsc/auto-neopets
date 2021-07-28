import os
import sys
import json
import glob
from pathlib import Path

sys.path[0] = ""
os.chdir("../data")
import neo
os.chdir("../conf")

filenames = ["secret-neo*", "secret-fai*"]

directories = [
    "", "/home/faith/Dropbox/Projects/neopets/neopets-cheats/conf/",
    "/home/faith/Dropbox/Projects/neopets/neopets-cheats-not-used/conf/",
    "/home/faith/neopets-cheats/conf/", "/home/faith/"
]

all_settings = []
valid_files = []
for directory in directories:
    for filename in filenames:
        all_filenames = list(
            glob.glob(str(Path(directory, filename).absolute())))
        for full_path in all_filenames:
            try:
                with open(full_path) as f:
                    file_contents = f.read()
                    if not file_contents:
                        file_contents = "{}"
                    all_settings.append(json.loads(file_contents))
                    valid_files.append(full_path)
            except:
                print("does not exist: {}".format(full_path))

all_usernames = []
for settings in all_settings:
    all_usernames.extend(list(settings.keys()))
all_usernames = sorted(list(set(all_usernames)))
new_secrets = {}

for username in all_usernames:
    new_secrets[username] = {}
    for settings in all_settings:
        if username in settings:
            for key, vals in settings[username].items():
                if key in new_secrets[username]:
                    if isinstance(new_secrets[username][key], list):
                        new_secrets[username][key].extend(
                            settings[username][key])
                        new_secrets[username][key] = sorted(
                            list(set(new_secrets[username][key])))
                else:
                    new_secrets[username][key] = settings[username][key]

for username in new_secrets:
    for key, vals in list(new_secrets[username].items()):
        if isinstance(new_secrets[username][key], list):
            while 0 in new_secrets[username][key]:
                new_secrets[username][key].remove(0)
            if new_secrets[username][key] == []:
                new_secrets[username].pop(key, None)

secrets = new_secrets
new_secrets = {}
for username in secrets.keys():
    if "loginfail" in secrets[username]:
        num_failed = len(secrets[username])
    else:
        num_failed = 0
    if num_failed not in new_secrets:
        new_secrets[num_failed] = []
    new_secrets[num_failed].append(username)
new_new_secrets = {}
for num_failed in sorted(new_secrets.keys()):
    for username in sorted(new_secrets[num_failed]):
        new_new_secrets[username] = secrets[username]
secrets = new_new_secrets

for username in secrets.keys():
    secrets[username]["tasks"] = ["trudy", "ghoul"]

with open("merged", "w") as f:
    f.write(json.dumps(secrets, indent=4))

for valid_file in valid_files:
    try:
        os.remove(valid_file)
    except:
        pass
os.rename("merged", "secret-neopets")

account = neo.Neo(None, None)
account.cleanUserConfig()
