import json
import string
import random
import datetime
from random_username.generate import generate_username

# Config
NUM_ACCOUNTS = 100
MIN_DATE = datetime.datetime(1980, 1, 1)
MAX_DATE = datetime.datetime(2003, 1, 1)
PASSWORD_SIZE = 20

# Do not edit below this line

DATE_DELTA = (MAX_DATE - MIN_DATE).days

VALID_PASSWORD_CHARTYPES = [
    string.digits, string.ascii_uppercase, string.ascii_lowercase
]
PASSWORD_CHARS = "".join(VALID_PASSWORD_CHARTYPES)


def get_random_date():
    return str((MIN_DATE +
                datetime.timedelta(days=random.randint(0, DATE_DELTA))).date())


def capitalizeString(s):
    return s[0].upper() + s[1:]


def checkValidPassword(password):
    for chartype in VALID_PASSWORD_CHARTYPES:
        if not any(x in chartype for x in password):
            return False
    return True


def generatePassword():
    validPassword = False
    while not validPassword:
        password = []
        for _ in range(PASSWORD_SIZE):
            password.append(random.choice(PASSWORD_CHARS))
        validPassword = checkValidPassword(password)
    return "".join(password)


usernames = generate_username(NUM_ACCOUNTS)
petnames = generate_username(NUM_ACCOUNTS)
passwords = [generatePassword() for _ in range(NUM_ACCOUNTS)]

usernames = [capitalizeString(x) for x in usernames]
passwords = [capitalizeString(x) for x in passwords]
petnames = [capitalizeString(x) for x in petnames]

with open("info") as f:
    info = json.loads(f.read())

cities = info["cities"]
emails = list(info["email_domains"].keys())
SECURITY_QUESTIONS = info["security_questions"]


def getSecurityAnswer(qn):
    answer = random.choice(SECURITY_QUESTIONS[qn]["words"])

    if SECURITY_QUESTIONS[qn]["prefix"]:
        without_prefix = random.choice(
            SECURITY_QUESTIONS[qn]["prefix"]) + " " + answer
        if len(without_prefix) >= 20:
            return answer
        answer = without_prefix

    if SECURITY_QUESTIONS[qn]["postfix"]:
        without_postfix = answer + " " + random.choice(
            SECURITY_QUESTIONS[qn]["postfix"])
        if len(without_postfix) >= 20:
            return answer
        answer = without_postfix

    return answer

account_info = {}
for i, (username, password, petname) in \
    enumerate(zip(usernames, passwords, petnames)):

    security_1 = random.choice(list(SECURITY_QUESTIONS.keys()))
    answer_1 = getSecurityAnswer(security_1)

    security_2 = security_1
    while security_2 == security_1:
        security_2 = random.choice(list(SECURITY_QUESTIONS.keys()))
    answer_2 = getSecurityAnswer(security_2)

    email = "{}@{}".format(username, random.choice(emails))

    account_info[username] = {
        "username": username,
        "password": password,
        "city": random.choice(cities),
        "birthdate": get_random_date(),
        "gender": "M" if random.random() < 0.5 else "F",
        "email": email,
        "petname": petname,
        "datecreated": datetime.datetime.now().strftime("%Y-%m-%d %H-%M"),
        "Security1": {
            "Question": security_1,
            "Answer": answer_1
        },
        "Security2": {
            "Question": security_2,
            "Answer": answer_2
        }
    }

with open("secret-account_info", "w") as f:
    f.write(json.dumps(account_info, indent=4))