# Retired as of 31 Dec, 2020
import time
import random
import base64
import hashlib
from datetime import datetime
import requests
from pyDes import PAD_PKCS5, triple_des
import logging
logging.basicConfig(
    format=
    "%(asctime)s.%(msecs)03d %(levelname)-5s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO)


class GhoulCatchers:
    def __init__(self, neo):
        self.neo = neo
        self.taskName = "ghoul"
        self.timeBetweenRuns = 6 * 60 * 60 # 6 hours
        self.minNp = 0
        self.enableNpCheck = True
        self.logStr = self.neo.username + " " + self.taskName + " "

        self.s = requests.session()
        self.api = "api.jumpstart.com"
        self.userid = None
        self.apitoken = None
        self.start_np = 0

        self.retries = 5

    def isRunnableTask(self):
        self.neo.createTaskData(self.taskName)
        return self.neo.runnableTask(self.taskName, self.timeBetweenRuns)

    def run(self):
        if self.isRunnableTask():
            if self.enableNpCheck:
                self.neo.maintainMinAmt(self.minNp)
                self.start_np = self.neo.getNp()
            self.loginParent()
            self.loginChild()
            self.sendScore()
            self.neo.updateLastRun(self.taskName)
            return True
        else:
            self.neo.displaySkipErrorMessage(self.taskName,
                                             self.timeBetweenRuns)
            return False

    def getTicks(self, dateObject):
        return (dateObject - datetime(1, 1, 1)).total_seconds() * 10000000

    def decryptData(self, data):
        decriptionKey = "AFDF51E3-063E-496B-8762-260063880244"
        encodedKey = decriptionKey.encode("utf-16-le")
        decriptionHash = hashlib.md5()
        decriptionHash.update(encodedKey)
        finalKey = decriptionHash.digest()
        tDes = triple_des(finalKey)
        return tDes.decrypt(base64.b64decode(data))

    def encyptData(self, data):
        decriptionKey = "AFDF51E3-063E-496B-8762-260063880244"
        encodedKey = decriptionKey.encode("utf-16-le")
        decriptionHash = hashlib.md5()
        decriptionHash.update(encodedKey)
        finalKey = decriptionHash.digest()
        tDes = triple_des(finalKey)
        enc = tDes.encrypt(data.encode("utf-16-le"), padmode=PAD_PKCS5)
        return enc

    def loginParent(self):
        url = "https://%s/Common/v3/AuthenticationWebService.asmx/LoginParent" % self.api
        encryptedData = self.encyptData(
            '<?xml version="1.0" encoding="utf-16"?>' +
            '<ParentLoginData xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            + 'xmlns:xsd="http://www.w3.org/2001/XMLSchema">' + '<UserName>' +
            self.neo.username + '</UserName>' + '<Password>' +
            self.neo.password + '</Password>' + '<Locale>en-US</Locale>' +
            '<FacebookAccessToken />' + '<ExternalUserID xsi:nil="true" />' +
            '<ExternalAuthData xsi:nil="true" />' +
            '<email xsi:nil="true" />' + '<SubscriptionID>0</SubscriptionID>' +
            '<ReceivesEmail>false</ReceivesEmail>' +
            '<AutoActivate xsi:nil="true" />' +
            '<SendActivationEmail xsi:nil="true" />' +
            '<SendWelcomeEmail xsi:nil="true" />' +
            '<LinkUserToFaceBook xsi:nil="true" />' +
            '<FavouriteTeamID xsi:nil="true" />' +
            '<GroupID xsi:nil="true" />' + '<UserPolicy>' +
            '<TermsAndConditions>true</TermsAndConditions>' +
            '<PrivacyPolicy>true</PrivacyPolicy>' + '</UserPolicy>' +
            '</ParentLoginData>')
        data = {
            "apiKey": "4a8b1082-5a88-40fc-a9f0-44ced5699267",
            "parentLoginData": base64.b64encode(encryptedData)
        }
        resp = self.s.post(url, data=data)
        encryptedData = self.neo.getBetween(resp.text, "<string>", "</string>")
        decryptedData = self.decryptData(encryptedData)
        self.apitoken = self.neo.getBetween(decryptedData.decode("utf-16-le"),
                                            "<ApiToken>", "</ApiToken>")
        self.userid = self.neo.getBetween(decryptedData.decode("utf-16-le"),
                                          "<UserID>", "</UserID>")
        logging.info(self.logStr + "Logged in")

    def loginChild(self):
        url = "https://%s/Common/AuthenticationWebService.asmx/LoginChild" % self.api
        _ticks = int(self.getTicks(datetime.utcnow()))
        _childId = self.encyptData(self.userid)
        a, b, c, e, f = str(
            _ticks
        ), "AFDF51E3-063E-496B-8762-260063880244", self.apitoken, base64.b64encode(
            _childId).decode(), "en-US"
        _s = a + b + c + e + f
        data = {
            "apiKey": "4a8b1082-5a88-40fc-a9f0-44ced5699267",
            "parentApiToken": self.apitoken,
            "ticks": str(_ticks),
            "signature": hashlib.md5(_s.encode()).hexdigest(),
            "childUserID": base64.b64encode(_childId).decode(),
            "locale": "en-US"
        }
        resp = self.s.post(url, data=data)
        _apitoken = self.neo.getBetween(resp.text, "<string>", "</string>")
        self.apitoken = self.decryptData(_apitoken).decode("utf-16-le")[:-4]

    def sendScore(self):
        numRounds = random.randint(51, 59)
        lastCheckedNpRound = 0
        isLate = self.neo.getNeopianHour() >= 17
        roundSleepTimeMin = 5
        roundSleepTimeMax = 9
        randomCheckProbability = 0.3
        if isLate:
            roundSleepTimeMin = 3
            roundSleepTimeMax = 5
            randomCheckProbability = 0.15

        for x in range(1, numRounds + 1):
            # Sleep some time to simulate playing the game
            sleep_time = random.random() + random.randint(
                roundSleepTimeMin, roundSleepTimeMax)
            time.sleep(sleep_time)

            url = "https://api.jumpstart.com/Achievement/AchievementWebService.asmx/ApplyPayout"
            _ticks = int(self.getTicks(datetime.utcnow()))
            a, b, c, d, e = str(
                _ticks
            ), "AFDF51E3-063E-496B-8762-260063880244", self.apitoken, "GCElementMatch", "300"
            _s = a + b + c + d + e
            data = {
                "apiToken": self.apitoken,
                "apiKey": "4a8b1082-5a88-40fc-a9f0-44ced5699267",
                "ModuleName": "GCElementMatch",
                "points": "300",
                "ticks": str(_ticks),
                "signature": hashlib.md5(_s.encode()).hexdigest()
            }

            # Send score to server, retry sometimes if it doesn't work
            try:
                self.s.post(url, data=data)
            except Exception as e:
                logging.error(self.logStr + str(e))
                for retry in range(self.retries):
                    logging.info(
                        self.logStr +
                        "Retrying {} of {}".format(retry, self.retries))
                    time.sleep(random.randint(3, 6))
                    try:
                        self.s.post(url, data=data)
                        break
                    except Exception as ee:
                        logging.error(self.logStr + str(ee))

            logging.info(self.logStr +
                         "Score sent ({}/{})".format(x, numRounds))

            # Randomly check that the score actually resulted in NP credited
            if self.enableNpCheck and (
                    x <= 2 or random.random() < randomCheckProbability):
                # Wait some time for the score to go through
                time.sleep(random.randint(2, 3) + random.random())
                try:
                    self.current_np = self.neo.getNp()
                    if self.current_np is not None:
                        if self.start_np is not None:
                            if (self.current_np - self.start_np
                                ) < (x - lastCheckedNpRound) * 1000:
                                logging.info(
                                    self.logStr +
                                    "Score did not go through -- exiting")
                                return
                        else:
                            logging.info(
                                "Could not retrieve starting np -- continuing")
                        lastCheckedNpRound = x
                        self.start_np = self.current_np
                    else:
                        logging.info(
                            self.logStr +
                            "Could not retrieve current np -- continuing")

                except Exception as e:
                    logging.info(self.logStr + str(e))
