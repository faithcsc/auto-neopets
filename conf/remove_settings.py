import json
from pathlib import Path

FILENAMES = list(Path("").glob("secret-neo*")) + \
            list(Path("").glob("secret-fai*"))
FILENAMES = sorted(FILENAMES)

for filename in FILENAMES:
    with open(filename) as f:
        settings = json.loads(f.read())

    remove_keys = [
        "loginattempt", "loginfail", "bankmanager", "nponhand", "npinbank"
    ]

    new_settings = {}
    for username, user_settings in settings.items():
        new_settings[username] = {}
        for key, vals in user_settings.items():
            if key not in remove_keys:
                if key == "trudy" or key == "ghoul":
                    new_settings[username][key] = [sorted(vals)[-1]]
                else:
                    new_settings[username][key] = vals

    with open(filename, "w") as f:
        f.write(json.dumps(new_settings, indent=4))
