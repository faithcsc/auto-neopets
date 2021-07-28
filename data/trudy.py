import logging
logging.basicConfig(
    format=
    "%(asctime)s.%(msecs)03d %(levelname)-5s %(filename)s:%(lineno)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO)


class Trudy:
    def __init__(self, neo):
        self.neo = neo
        self.taskName = "trudy"
        self.timeBetweenRuns = 7 * 60 * 60 # 7 hours
        self.minNp = 0
        self.logStr = self.neo.username + " " + self.taskName + " "

        self.claimPrizeURL = "trudydaily/ajax/claimprize.php"

    def isRunnableTask(self):
        self.neo.createTaskData(self.taskName)
        return self.neo.runnableTask(self.taskName, self.timeBetweenRuns)

    def run(self):
        if self.isRunnableTask():
            self.neo.maintainMinAmt(self.minNp)

            for attempts in range(2):
                resp = self.neo.get('trudys_surprise.phtml?delevent=yes',
                                    'https://www.jellyneo.net/?go=dailies')
                if resp is not None:
                    break
            if resp is None:
                logging.error(self.logStr +
                              "Could not retrieve trudy page. Exiting")
                return

            if self.neo.contains(resp.text, "&slt=1"):
                result = self.neo.getBetween(resp.text, 'phtml?id=',
                                             '" name="')
                resp = self.neo.get('trudydaily/slotgame.phtml?id=%s' % result,
                                    resp.url)
                results = self.neo.getBetween(resp.text, '\'key\': \'', '\'};')

                resp = self.neo.post(
                    self.claimPrizeURL,
                    data={
                        'action': 'getslotstate',
                        'key': results
                    },
                    headers={
                        "Referer":
                        'http://www.neopets.com/trudydaily/slotgame.phtml?id=%s'
                        % result
                    })
                resp = self.neo.post(self.claimPrizeURL,
                                     data={'action': 'beginroll'},
                                     headers={"Referer": resp.url})
                self.neo.post(self.claimPrizeURL,
                              data={'action': 'prizeclaimed'},
                              headers={"Referer": resp.url})
                self.neo.displaySuccessMessage(self.taskName)
            else:
                logging.info(self.logStr + "Already done today")
            self.neo.updateLastRun(self.taskName)
            return True
        else:
            self.neo.displaySkipErrorMessage(self.taskName,
                                             self.timeBetweenRuns)
            return False
