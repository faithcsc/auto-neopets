import json
import time
import random
import pickle
import logging
from datetime import datetime
import pytz
import requests

logging.basicConfig(
    format=
    "%(asctime)s.%(msecs)03d %(levelname)-5s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO)
USER_CONFIG_FILE = "../conf/secret-neopets"
FAIL_CONFIG_FILE = "../conf/secret-failed"
SETTINGS_FILE = "../conf/settings"
SESSIONS_FOLDER = "../conf/secret-sessions"


class Neo:
    def __init__(self, username, password):
        if username and password:
            self.username = username
            self.password = password
        else:
            self.username = ""
            self.password = ""
            logging.info(
                "Invalid Username: '{}', Password: '{}', using empty profile".
                format(username, password))
        self.loadSettings()
        self.loadUserData()

        self.s = self.loadSesssionFile(self.username)
        self.saveSesssionFile()
        self.base = "http://www.neopets.com/"
        self.setHeaders()
        self.cookies = None

        self.bank_url = "bank.phtml"
        self.postBankUrl = "process_bank.phtml"

        # Check if bank interest has been collected in this session
        self.collectedBankInterest = False
        self.upgradedBankAccount = False

        self.NPOnHand = None
        self.NPInBank = None
        self.latestRetrievedPage = None
        self.latestRetrievedBankPage = None
        self.loginTimeout = 3600
        self.discardEpochOlderThan = 2 * 24 * 60 * 60  # 2 days
        self.failThreshold = 6

    def loadUserData(self):
        with open(USER_CONFIG_FILE) as f:
            self.config = json.loads(f.read())
        if self.username and self.password and self.username not in self.config:
            self.config[self.username] = {
                "username": self.username,
                "password": self.password
            }
        for username, user_data in self.config.items():
            for task, task_values in user_data.items():
                if type(task_values) == list:
                    self.config[username][task] = sorted(task_values,
                                                         reverse=True)
        self.saveConfigFile()

    def loadSesssionFile(self, username):
        if self.username and self.config[self.username]["sessionPersist"]:
            try:
                sessionPersistedFrom = self.config[username].get(
                    "sessionPersistedFrom", 0)
                currentTime = int(time.time())
                cutoffTime = currentTime = self.discardEpochOlderThan
                if sessionPersistedFrom > cutoffTime:
                    with open("{}/{}".format(SESSIONS_FOLDER,
                                             self.username)) as f:
                        session = pickle.load(f)
                    return session
            except:
                pass
            session = requests.session()
            self.config[username]["sessionPersistedFrom"] = int(time.time())
            self.saveConfigFile()
            return session
        else:
            return requests.session()

    def saveSesssionFile(self):
        if self.username and self.config[self.username]["sessionPersist"]:
            with open("{}/{}".format(SESSIONS_FOLDER, self.username),
                      "wb") as f:
                pickle.dump(self.s, f)

    ## LOGGING INTO WEBSITE

    def checkIfShouldLogin(self):
        return self.runnableTask("loginattempt", self.loginTimeout) and \
               self.runnableTask("loginfail", self.loginTimeout)

    def doLogin(self):
        # Try logging in only once every 1 hour
        if self.checkIfShouldLogin():
            for _ in range(logging.infoinRetries):
                resp = self.tryLogin()
                if resp is None:
                    return False
                if self.checkIfLoginSuccess(resp):
                    self.config[self.username]["loginfail"] = []
                    return True
            self.createUserConfigValue("loginfail", int(time.time()))
            logging.info(self.username + " Login fail")
        else:
            logging.info(
                self.username +
                " Last login attempt at {}, less than {} hours ago".format(
                    self.getNeopianTime(self.lastRun("loginattempt")),
                    round(self.loginTimeout / 3600.0, 2)))
        return False

    def checkLoginPage(self, resp):
        checkLoginPageContents = [
            "no username found! please go back and re-enter your username"
        ]
        for checkLoginPageContent in checkLoginPageContents:
            if checkLoginPageContent not in resp.text.lower():
                logging.info(
                    self.username +
                    " {} not in resp.text".format(checkLoginPageContent))
                logging.info("{}".format(resp.text.lower()))
                return None
        return resp

    def tryLogin(self):
        self.updateLastRun("loginattempt")

        resp = self.get("login.phtml")
        resp = self.checkLoginPage(resp)
        if resp is None:
            return None

        loginHeaders = {
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Origin": "http://www.neopets.com",
            "Upgrade-Insecure-Requests": "1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept":
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Referer": "http://www.neopets.com/login/",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,th;q=0.7"
        }

        resp = self.post("login.phtml",
                         data={
                             "destination": "",
                             "return_format": "1",
                             "username": self.username,
                             "password": self.password
                         },
                         headers=loginHeaders)

        return resp

    def checkIfLoginSuccess(self, resp):
        success = False
        if "<title>Neopets - Hi!</title>" not in resp.text and \
            "<title>Neopets - Error 404</title>" not in resp.text and \
            resp.text.find("npanchor") > 1:
            success = True
        if success:
            logging.info(self.username + " Login success")
        else:
            logging.info(self.username + " Login fail")
        return success

    ## LOGGING

    def contains(self, data, subdata):
        return subdata.lower() in data.lower()

    def formatFloat(self, floatValue):
        if int(floatValue) == float(floatValue):
            return str(int(floatValue))
        return str(round(floatValue, 3))

    def formatSeconds(self, seconds):
        if seconds is None:
            return "24 hours"
        if seconds <= 60:
            return "{} seconds".format(seconds)
        if seconds <= 60 * 60:
            return "{} minutes".format(self.formatFloat(seconds / 60.0))
        if seconds <= 24 * 60 * 60:
            return "{} hours".format(self.formatFloat(seconds / (60.0 * 60.0)))
        return "{} days".format(self.formatFloat(seconds / (24 * 60.0 * 60.0)))

    def displaySkipErrorMessage(self, taskName, timeBetweenRuns):
        last_run_time = self.lastRun(taskName)
        last_run_time = self.getNeopianTime(last_run_time)
        logging.info(
            "{} {} Skipped Last run time: {} Neopian Time, less than {} ago ".
            format(self.username, taskName, last_run_time,
                   self.formatSeconds(timeBetweenRuns)))

    def displaySuccessMessage(self, taskName):
        logging.info(self.username + " {} Done".format(taskName))

    def getBetween(self, data, first, last):
        try:
            return data.split(first)[1].split(last)[0]
        except Exception as e:
            logging.info(self.username + " getBetween does not exist")
            logging.info(self.username + " {}".format(first))
            logging.info(self.username + " {}".format(last))

    ## REQUESTS

    def url(self, path):
        return "{}{}".format(self.base, path)

    def setHeaders(self):
        self.s.headers.update({
            "User-Agent":
            self.userAgent,
            "Accept":
            "text/html,application/xhtml+xml,application/xml;" +
            "q=0.9,image/avif,image/webp,image/apng," +
            "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding":
            "gzip, deflate",
            "Accept-Language":
            "en-GB,en;q=0.9",
            "Connection":
            "keep-alive",
            "Pragma":
            "no-cache",
            "Cache-Control":
            "no-cache",
            "DNT":
            "1",
            "Upgrade-Insecure-Requests":
            "1",
        })

    def get(self, path, referer=None, params=None):
        logging.info(self.username + " [GET] {}".format(path))
        time.sleep(random.uniform(self.minDelay, self.maxDelay))
        url = self.url(path)
        if referer:
            self.s.headers.update({"Referer": referer})
            
        logging.info(self.username + " [GET] {} headers: {}".format(path, self.s.headers))
        try:
            logging.info(self.username + " [GET] {} cookies: {}".format(path, self.s.cookies))
        except:
            pass

        try:
            if params:
                resp = self.s.get(url, params=params, timeout=self.timeout)
            else:
                resp = self.s.get(url, timeout=self.timeout)
            self.cookies = dict(resp.cookies)
        except requests.exceptions.ReadTimeout as e:
            logging.error("{} [GET] {} timeout".format(self.username, path))
            return None
        except Exception as e:
            logging.error("{} [GET] {} error: {}".format(
                self.username, path, e))
            return None

        logging.info(self.username + " [GET] {} headers: {}".format(path, self.s.headers))
        try:
            logging.info(self.username + " [GET] {} cookies: {}".format(path, self.s.cookies))
        except:
            pass
        
        if "Referer" in self.s.headers:
            del self.s.headers["Referer"]

        self.latestRetrievedPage = resp

        # Collect interest
        # Parse NP in bank and on hand
        if "bank" in self.checkReturnedPageContent(resp).lower():
            self.latestRetrievedBankPage = resp
            try:
                self.parseNPInBank()
                self.parseNPOnHand()
            except:
                pass
            self.collectBankInterest(resp)
            self.upgradeBankAccount(resp)

        self.checkReturnedPageContent(resp)

        return resp

    def post(self, path, data=None, headers=None):
        logging.info(self.username + " [POST] {}".format(path))
        time.sleep(random.uniform(self.minDelay, self.maxDelay))

        originalHeaders = self.s.headers

        if headers and headers.keys(
        ) and self.s.headers and self.s.headers.keys():
            logging.debug("headers: {}".format(headers))
            logging.debug("self.s.headers: {}".format(self.s.headers))
            self.s.headers.update(headers)

        url = self.url(path)

        if data:
            logging.debug("[POST] {} data = {}".format(path, data))
        if self.cookies:
            logging.debug("[POST] {} cookies = {}".format(path, self.cookies))
        if headers:
            logging.debug("[POST] {} headers = {}".format(
                path, self.s.headers))
            
        logging.info(self.username + " [POST] {} headers: {}".format(path, self.s.headers))
        try:
            logging.info(self.username + " [POST] {} cookies: {}".format(path, self.s.cookies))
        except:
            pass

        for _ in range(2):
            try:
                if data:
                    resp = self.s.post(url,
                                       data=data,
                                       timeout=self.timeout,
                                       cookies=self.cookies)
                else:
                    resp = self.s.post(url,
                                       timeout=self.timeout,
                                       cookies=self.cookies)
                break
            except requests.exceptions.ReadTimeout as e:
                logging.error("{} [GET] {} timeout".format(
                    self.username, path))
                self.s.headers = originalHeaders
                return None
            except Exception as e:
                logging.error("{} [GET] {} error: {}".format(
                    self.username, path, e))
                self.s.headers = originalHeaders
                return None
            
        logging.info(self.username + " [POST] {} headers: {}".format(path, self.s.headers))
        try:
            logging.info(self.username + " [POST] {} cookies: {}".format(path, self.s.cookies))
        except:
            pass

        self.s.headers = originalHeaders

        self.latestRetrievedPage = None
        self.latestRetrievedBankPage = None

        self.checkReturnedPageContent(resp)

        return resp

    ## CONFIGURATION

    def loadSettings(self):
        """Load general settings like userAgent, delay timings"""
        with open(SETTINGS_FILE) as f:
            settings = json.loads(f.read())
        self.userAgent = settings["UserAgent"]
        self.minDelay = float(settings["MinDelay"])
        self.maxDelay = float(settings["MaxDelay"])
        self.timeout = float(settings["Timeout"])
        logging.infoinRetries = int(settings["FailedLoginRetries"])

    def saveConfigFile(self):
        with open(USER_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def createUserConfigValue(self, task, value):
        if str(task) and str(value):
            if task not in self.config[self.username]:
                self.config[self.username][task] = []
            self.config[self.username][task].insert(0, value)
            self.saveConfigFile()
        else:
            logging.error(
                "Invalid data for {}: Task: '{}', Value: '{}'".format(
                    self.username, task, value))

    def createTaskData(self, task):
        if self.username in self.config and task in self.config[self.username]:
            return
        self.createUserConfigValue(task, 0)

    def removeOldEpochs(self, epoch_list, older_than):
        """From a list of epoch times epoch_list, remove epochs older than 
        current time minus older_than."""
        current_time = int(time.time())
        time_cutoff = current_time - older_than
        return [x for x in epoch_list if x > time_cutoff]

    def cleanUserConfig(self):
        try:
            with open(FAIL_CONFIG_FILE) as f:
                failed = json.loads(f.read())
        except FileNotFoundError:
            failed = {}
        self.config.update(failed)

        new_datas = {}
        current_time = int(time.time())
        for user, x in self.config.items():
            new_data = {
                "username": x["username"],
                "password": x["password"],
                "city": x["city"],
                "birthdate": x["birthdate"],
                "gender": x["gender"],
                "email": x["email"],
                "petname": x["petname"],
                "tasks": x.get("tasks", ["trudy"])
            }
            for optional_item in [
                    "nponhand", "npinbank", "sessionPersistedFrom",
                    "sessionPersist", "Security1", "Security2", "datecreated"
            ]:
                if optional_item in x:
                    new_data.update({optional_item: x[optional_item]})
            task_data = {}
            for name, values in self.config[user].items():
                if name not in new_data:
                    if type(self.config[user][name]) == list:
                        if 0 in self.config[user][name]:
                            self.config[user][name].remove(0)
                        self.config[user][name] = sorted(
                            self.config[user][name])
                    if self.config[user][name] not in [[], [0]]:
                        task_data.update({name: self.config[user][name]})
            new_data.update(task_data)
            new_datas.update({user: new_data})
        self.config = new_datas

        # Sort usernames by most failed logins within last 2 days first
        loginfails = {}
        for user, x in self.config.items():
            # Remove failed logins older than 2 days
            # So that we can retry logging in again
            failedRecentLogins = self.removeOldEpochs(
                self.config[user].get("loginfail", []),
                self.discardEpochOlderThan)
            loginfails.update({user: len(failedRecentLogins)})
        loginfails = dict(sorted(loginfails.items(), key=lambda item: item[1]))

        # Keep only usernames with fewer than 6 failed logins over 2 days
        # Place the rest in the failed file so we don't retry logging in again
        data = {}
        failed = {}
        for user, fail_times in loginfails.items():
            if fail_times < self.failThreshold:
                data.update({user: self.config[user]})
            else:
                failed.update({user: self.config[user]})
        self.config = data

        # Sort users by least NP first
        for users_dictionaries in [self.config, failed]:
            for k, v in users_dictionaries.items():
                for attr in ["nponhand", "npinbank"]:
                    if attr not in users_dictionaries[k]:
                        users_dictionaries[k][attr] = -1
            users_dictionaries = {
                k: v
                for k, v in sorted(
                    users_dictionaries.items(),
                    key=lambda item: item[1]["npinbank"] + item[1]["nponhand"])
            }

        with open(USER_CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

        with open(FAIL_CONFIG_FILE, "w") as f:
            json.dump(failed, f, indent=4)

    ## TIME

    def getNeopianTime(self, timestamp):
        return datetime.fromtimestamp(timestamp).astimezone(
            pytz.timezone("US/Pacific"))

    def getNeopianHour(self):
        return self.getNeopianTime(time.time()).hour

    def lastRun(self, task):
        if task in self.config[self.username]:
            if self.config[self.username][task]:
                return float(max(self.config[self.username][task]))
        return 0

    def runnableTask(self, task, timeDiffSeconds=None):
        current_time = self.getNeopianTime(int(time.time()))
        last_run_time = self.getNeopianTime(self.lastRun(task))
        is_new_day = (current_time.date() - last_run_time.date()).days >= 1
        if timeDiffSeconds is None:
            return is_new_day
        return is_new_day or (current_time -
                              last_run_time).total_seconds() >= timeDiffSeconds

    def updateLastRun(self, task):
        if task not in self.config[self.username]:
            self.config[self.username][task] = []
        self.config[self.username][task].append(int(time.time()))
        self.saveConfigFile()

    ## NEOPOINTS

    def checkReturnedPageContent(self, resp):
        if "<title>Neopets - Hi!</title>" in resp.text:
            logging.debug("Response: not logged in!")
            return "Not logged in"
        elif "<title>Neopets - Error 404</title>" in resp.text:
            logging.debug("Response: could not find page. 404")
            return "Could not find page, 404"
        elif "may get angry and refuse to" in resp.text.lower():
            logging.debug("Bank page")
            return "Bank"
        else:
            logging.debug("Response: {}".format(resp.text))
            return "Normal page"

    def checkNewLayout(self, resp):
        # Check if this account is using the new mobile layout
        # And change the hidden referral values respectively
        self.isNewLayout = False
        self.postBankUrl = "bank.phtml"
        self.refCkName = "ref_ck"
        if self.contains(resp.text, "_2020"):
            self.isNewLayout = True
            self.postBankUrl = "np-templates/ajax/process_bank.php"
            self.refCkName = "_ref_ck"
            logging.debug("Using new bank layout")
        else:
            logging.debug("Using old bank layout")

        try:
            self.hidden_referral_value = self.getBetween(
                resp.text, "='{}' value='".format(self.refCkName), "'>")
            logging.debug("Bank hidden referral value: {}".format(
                self.hidden_referral_value))
        except Exception as e:
            logging.error(e)
            logging.debug("Could not get hidden referral value")
            self.hidden_referral_value = ""

        return self.isNewLayout

    def collectBankInterest(self, resp):

        if self.collectedBankInterest:
            logging.debug(self.username + " Already collected bank interest")
            return

        # Check that this is a valid bank page
        if "bank" not in self.checkReturnedPageContent(resp).lower():
            return resp

        # Check if this account is using the new mobile layout
        isNewLayout = self.checkNewLayout(resp)

        if self.contains(resp.text, "don't currently have an account"):
            self.createBank()
        elif self.contains(resp.text, "ou have deposited") and self.contains(
                resp.text, "withdrawn neopoints today"):
            logging.debug(
                self.username +
                " Deposited / withdrawn, cannot collect bank interest")
            self.collectedBankInterest = True
            return
        elif not isNewLayout and self.contains(
                resp.text, "already collected your interest"):
            logging.debug(self.username + " Already collected bank interest")
            self.collectedBankInterest = True
            return
        elif isNewLayout and self.contains(
                resp.text,
                "<p>You've already collected your interest today.</p>"):
            logging.debug(self.username + " Already collected bank interest")
            self.collectedBankInterest = True
            return
        elif not isNewLayout and self.contains(resp.text, "Collect Interest"):
            interest = self.getBetween(resp.text, "allow you to gain <b>",
                                       " NP</b> per ")
        elif isNewLayout and self.contains(
                resp.text, "type='submit' value='Collect Interest'>"):
            interest = self.getBetween(resp.text, "'>Daily Interest: ",
                                       " NP</div>")
            interest = str(interest).replace(",", "").replace(" ", "")
            interest = int(interest)

        resp = self.postToBank({
            "type": "interest",
        })

        # Check if returned response is a json or normal web page
        try:
            result = json.loads(str(resp.text).strip())
            if "success" in result:
                if result["success"]:
                    logging.info(self.username + " Collected %s NP interest" %
                                 result["interest_gain"])
                    self.collectedBankInterest = True
                else:
                    logging.info("Response: '{}'".format(result))
                    logging.error("Could not collect interest")
                    self.collectedBankInterest = True
                return
        except Exception as e:
            logging.error(e)

        if not isNewLayout and self.contains(
                resp.text, "already collected your interest"):
            logging.info(self.username +
                         " Collected %s NP interest" % interest)
            self.collectedBankInterest = True
        elif isNewLayout and self.contains(
                resp.text,
                "<p>You've already collected your interest today.</p>"):
            logging.info(self.username +
                         " Collected %s NP interest" % interest)
            self.collectedBankInterest = True
        else:
            logging.info("Response: {}".format(resp.text))
            logging.error("Could not collect interest")

        return

    def getNp(self):
        if self.get(self.bank_url) is None:
            return
        try:
            self.NPOnHand = self.parseNPOnHand()
        except Exception as e:
            logging.error(e)
            if self.get(self.bank_url) is None:
                return
            self.NPOnHand = self.parseNPOnHand()
        return self.NPOnHand

    def parseNPString(self, NPString):
        NPString = str(NPString).strip().replace(",", "").replace(" ", "")
        NPString = int(NPString)
        return NPString

    def parseNPInBank(self):
        if self.latestRetrievedBankPage is None:
            if self.get(self.bank_url) is None:
                return
        try:
            self.NPInBank = self.getBetween(
                self.latestRetrievedBankPage.text,
                "<span id='txtCurrentBalance1' class=''>Current Balance: ",
                " NP</span>")
        except Exception as e:
            logging.error(e)
            try:
                self.NPInBank = self.getBetween(
                    self.latestRetrievedBankPage.text,
                    "id='txtCurrentBalance' class='bank-text'>", "</span>")
            except Exception as e:
                logging.error(e)
                logging.info("Could not parse NP in bank.")

                self.checkReturnedPageContent(
                    self.latestRetrievedBankPage.text)

                return 0

        self.NPInBank = self.parseNPString(self.NPInBank)
        logging.info(self.username + " {} NP in bank".format(self.NPInBank))
        return self.NPInBank

    def parseNPOnHand(self):
        if self.latestRetrievedBankPage is None:
            if self.get(self.bank_url) is None:
                return
        try:
            self.NPOnHand = self.getBetween(
                self.latestRetrievedPage.text,
                "<span id=\"npanchor\" class=\"np-text__2020\">", "</span>")
        except Exception as e:
            logging.error(e)
            try:
                self.NPOnHand = self.getBetween(
                    self.latestRetrievedBankPage.text,
                    "id='npanchor' href=\"/inventory.phtml\">", "</a>")
            except:
                logging.error(e)
                logging.info("Could not parse NP on hand.")
                self.checkReturnedPageContent(
                    self.latestRetrievedBankPage.text)
                return 0

        self.NPOnHand = self.parseNPString(self.NPOnHand)
        logging.info(self.username + " {} NP on hand".format(self.NPOnHand))
        return self.NPOnHand

    def postToBank(self, data, headers=None):
        data.update({self.refCkName: self.hidden_referral_value})
        if headers:
            resp = self.post(self.postBankUrl, data=data, headers=headers)
        else:
            resp = self.post(self.postBankUrl, data=data)
        return resp

    def upgradeBankAccount(self, resp=None):
        if self.upgradedBankAccount:
            return
        self.upgradedBankAccount = True

        if resp is None:
            resp = self.get(self.bank_url)

        # Check current level and compare against known account types
        accountName = {
            "Junior Saver": 0,
            "Neopian Student": 1000,
            "Bronze Saver": 2500,
            "Silver Saver": 5000,
            "Super Gold Plus": 10000,
            "Platinum Extra": 25000,
            "Double Platinum": 50000,
            "Triple Platinum": 75000,
            "Diamond Deposit": 100000,
            "Diamond Deposit Plus": 250000,
            "Diamond Deposit Gold": 500000,
            "Millionaire Platinum": 1000000,
            "Millionaire Double Platinum": 2000000,
            "Millionaire Mega-Platinum": 5000000,
            "Neopian Mega-Riches": 7500000,
            "Ultimate Riches!": 10000000
        }

        # Retrieve current account level and check that it's not the max
        currentAccountType = self.getBetween(
            resp.text,
            "span class='bank-text-bold'>Account Type: </span><span id='txtAccountType' class='bank-text'>",
            "</span>")

        if currentAccountType == list(accountName.keys())[-1]:
            logging.info(self.username +
                         " Current account {} at max level, not upgrading".
                         format(currentAccountType))
            return

        # Check that it is upgradeable
        nextAccountType = list(accountName.keys())[
            list(accountName.keys()).index(currentAccountType) + 1]
        nextAccountNP = accountName[nextAccountType]
        if self.NPInBank < nextAccountNP:
            logging.info(self.username +
                         " Current account {} at correct level, not upgrading".
                         format(currentAccountType))
            return

        # Get the max account upgradeable
        maxAccountType = 0
        for i, key in enumerate(list(accountName.keys())):
            if accountName[key] > self.NPInBank:
                break
            maxAccountType = i

        logging.info(self.username +
                     " Current account {}, upgrading to {} {}".format(
                         currentAccountType,
                         list(accountName.keys())[maxAccountType], accountName[
                             list(accountName.keys())[maxAccountType]]))

        if self.NPOnHand == 0:
            self.withdrawNp(1, None, resp)

        resp = self.postToBank({
            "type": "upgrade",
            "account_type": str(maxAccountType),
            "amount": str(self.NPOnHand)
        })

        logging.info(self.username + " Response: {}".format(resp.text))

    def depositNp(self, np, deposit_all=False):
        resp = self.get(self.bank_url)
        if resp is None:
            return
        if self.contains(resp.text, "don't currently have an account"):
            self.createBank()

        # Check if this account is using the new mobile layout
        self.checkNewLayout(resp)

        if deposit_all:
            try:
                np = self.parseNPOnHand()
            except Exception as e:
                logging.error(e)
                return

        if np > 0:
            resp = self.postToBank({"type": "deposit", "amount": str(np)})

            self.checkReturnedPageContent(resp)
            if resp is None:
                return
            logging.info(self.username + " Deposited %s NP" % np)
            self.collectedBankInterest = True
        else:
            logging.info(self.username + " No NP to deposit")

    def depositAllNp(self):
        self.depositNp(0, deposit_all=True)
        try:
            self.parseNPInBank()
            self.config[self.username]["nponhand"] = self.NPOnHand
            self.saveConfigFile()
        except Exception as e:
            logging.error(e)
            return
        try:
            self.parseNPOnHand()
            self.config[self.username]["npinbank"] = self.NPInBank
            self.saveConfigFile()
        except Exception as e:
            logging.error(e)
            return

    def createBank(self, resp=None):
        if resp is None:
            resp = self.get(self.bank_url)

        # Check current level and compare against known account types
        accountName = {
            "Junior Saver": 0,
            "Neopian Student": 1000,
            "Bronze Saver": 2500,
            "Silver Saver": 5000,
            "Super Gold Plus": 10000,
            "Platinum Extra": 25000,
            "Double Platinum": 50000,
            "Triple Platinum": 75000,
            "Diamond Deposit": 100000,
            "Diamond Deposit Plus": 250000,
            "Diamond Deposit Gold": 500000,
            "Millionaire Platinum": 1000000,
            "Millionaire Double Platinum": 2000000,
            "Millionaire Mega-Platinum": 5000000,
            "Neopian Mega-Riches": 7500000,
            "Ultimate Riches!": 10000000
        }

        # Retrieve current account level and check that it's not the max
        currentAccountType = self.getBetween(
            resp.text,
            "span class='bank-text-bold'>Account Type: </span><span id='txtAccountType' class='bank-text'>",
            "</span>")
        logging.info(self.username +
                     " currentAccountType: {}".format(currentAccountType))
        if currentAccountType == list(accountName.keys())[-1]:
            logging.info(self.username +
                         " Current account at max level, not upgrading")
            return

        # Check that it is upgradeable
        nextAccountType = list(accountName.keys())[
            list(accountName.keys()).index(currentAccountType) + 1]
        nextAccountNP = accountName[nextAccountType]
        if self.NPInBank < nextAccountNP:
            logging.info(self.username +
                         " Current account at correct level, not upgrading")
            return

        # Get the max account upgradeable
        maxAccountType = 0
        for i, key in enumerate(list(accountName.keys())):
            if accountName[key] > self.NPInBank:
                break
            maxAccountType = i

        logging.info(self.username + " Creating account: {} {}".format(
            list(accountName.keys())[maxAccountType], accountName[list(
                accountName.keys())[maxAccountType]]))

        if self.NPOnHand == 0:
            self.withdrawNp(1, None, resp)

        resp = self.postToBank(
            {
                "type": "new_account",
                "name": "x",
                "add1": "n",
                "employment": "Chia Custodian",
                "salary": "10,000 NP and below",
                "account_type": str(maxAccountType),
                "amount": str(self.NPOnHand)
            },
            headers={"Referer": resp.url})
        if self.contains(resp.text, "Activation Code"):
            logging.info("Account not activated, cannot create bank account")
        else:
            logging.info("Created a bank account")

        logging.info(self.username + " Response: {}".format(resp.text))
        return

        # # TODO update to use upgradeBankAccount template

    def withdrawNp(self, np, pin=None, resp=None):
        if resp is None:
            resp = self.get(self.bank_url)
        if resp is None:
            return

        if self.contains(resp.text, "don't currently have an account"):
            self.createBank()
        if self.contains(resp.text, "Enter your"):
            result = self.postToBank(
                {
                    "type": "withdraw",
                    "amount": str(np),
                    "pin": str(pin)
                },
                headers={"Referer": resp.url})
        else:
            result = self.postToBank({
                "type": "withdraw",
                "amount": str(np)
            },
                                     headers={"Referer": resp.url})
        if result is None:
            logging.error("No result returned")
            return
        logging.info("Response: {}".format(result.text))
        logging.info(self.username + " Withdrew %s NP" % np)
        self.collectedBankInterest = True
        self.NPOnHand = self.getNp()

    def withdrawAllNp(self):
        self.NPInBank = self.parseNPInBank()
        self.withdrawNp(self.NPInBank, "")

    def maintainMinAmt(self, np):
        if np <= 0:
            return
        self.NPOnHand = self.getNp()
        if self.NPOnHand > np:
            logging.info(
                self.username +
                " {} NP on hand, more than {}".format(self.NPOnHand, np))
            return
        self.withdrawNp(np - self.NPOnHand, "")
