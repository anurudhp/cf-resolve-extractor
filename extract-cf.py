import json
import sys
import xml.etree.ElementTree as ET

data = json.load(open(sys.argv[1]))
if data['status'] != 'OK':
    print(data)
    sys.exit(1)

##############################################################################
### Parse CF submission data                                              ####
##############################################################################

data = data['result'] # list of submissions
'''sample submission:
{
    "id":142710388,
    "contestId":364369,
    "creationTimeSeconds":1642169782,
    "relativeTimeSeconds":382,
    "problem":{
        "contestId":364369,
        "index":"C",
        "name":"Shortest Path!",
        "type":"PROGRAMMING",
        "tags":[]
    },
    "author":{
        "contestId":364369,
        "members":[{"handle":"codelegend"}],
        "participantType":"CONTESTANT",
        "teamId":22100,
        "teamName":"tesla_protocol",
        "ghost":false,
        "startTimeSeconds":1642169400
    },
    "programmingLanguage":"GNU C++17 (64)",
    "verdict":"OK",
    "testset":"TESTS",
    "passedTestCount":3,
    "timeConsumedMillis":1419,
    "memoryConsumedBytes":0
}
'''

# teamId -> (teamName, members)
teams = dict()

for sub in data:
    team = sub['author']['teamId']
    teamname = sub['author']['teanName']
    members = sub['author']['members']
    teams[team] = (teamname, members)

    prob = sub['problem']['index']
    timestamp = sub['creationTimeSeconds']
    subtime = sub['relativeTimeSeconds']
    verdict = 'OK' if sub['verdict'] == 'OK' else 'WRONG'
    print(sub['id'])

##############################################################################
### Produce final contest feed (xml)                                      ####
##############################################################################

output_feed = ET.element('contest')

