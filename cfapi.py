import random
import string
import time
import hashlib

import config

class APICall():
    def __init__(self, method, auth=False):
        self.method = method
        self.opts = []
        self.call = ''
        self.auth = auth
    def add(self, param, value):
        self.opts.append((str(param), str(value)))
    def build(self):
        self.opts.sort()
        self.call = self.method
        pref = '?'
        for (p, v) in self.opts:
            self.call = self.call + pref + p + '=' + v
            pref = '&'

    def sign(self):
        self.add('apiKey', config.api_key)
        self.add('time', int(time.time()))
        self.build()

        # signing
        rnd = ''.join(random.choices('123456789', k=6))
        secret = rnd + '/' + self.call + '#' + config.secret
        h = hashlib.sha512(secret.encode('utf-8'))
        hash_value = h.hexdigest()
        self.call = self.call + '&apiSig=' + rnd + hash_value

    def get_url(self):
        if self.call == '':
            if self.auth:
                self.sign()
            else:
                self.build()
        return 'https://codeforces.com/api/' + self.call

# Usage:
# call = APICall('contest.status', auth=True)
# call.add('contestId', 566)
# call.add('from', 1)
# call.add('count', 10)
# print(call.get_url())
# check https://codeforces.com/apiHelp for all methods
