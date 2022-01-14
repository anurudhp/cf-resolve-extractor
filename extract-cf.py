import json
import sys
import os.path
import argparse
import sh
import time
import xml.etree.ElementTree as ET

import config
from cfapi import APICall

if len(sys.argv) < 4:
    print(f'Usage: python3 {sys.argv[0]} <status>.json <standings>.json <output>.xml')
    sys.exit(1)

# GLOBAL
status_file = sys.argv[1]
standings_file = sys.argv[2]
output_file = sys.argv[3]

##############################################################################
### Query API if file isn't present                                       ####
##############################################################################

if not os.path.isfile(status_file):
    print('Fetching status...', end='', flush=True)
    call = APICall('contest.status', True)
    call.add('contestId', config.contest_id)
    call.add('from', 1)
    call.add('count', 5000)
    url = call.get_url()
    time.sleep(1)
    sh.wget(url, '-O', status_file)
    print('Done!')

if not os.path.isfile(standings_file):
    print('Fetching standings...', end='', flush=True)
    call = APICall('contest.standings', True)
    call.add('contestId', config.contest_id)
    call.add('from', 1)
    call.add('count', 1)
    url = call.get_url()
    time.sleep(1)
    sh.wget(url, '-O', standings_file)
    print('Done!')

##############################################################################
### Extract CF contest problem list                                       ####
##############################################################################

def extract_problem_data():
    data = json.load(open(standings_file))
    assert(data['status'] == 'OK')
    data = data['result']

    contest_details = data['contest']
    length = data['contest']['durationSeconds']
    contest_details['length'] = '%02d:%02d:%02d' % (length//3600, (length/60)%60, length%60)

    problems = [] # list of (problem_code, problem_name)
    problem_ids = dict() # problem_code -> index+1
    for prob in data['problems']:
        code = prob['index']
        name = prob['name']
        problems.append((code, name))
        problem_ids[code] = len(problems)

    return (contest_details, problems, problem_ids)

# GLOBAL
contest_details, problems, problem_ids = extract_problem_data()

##############################################################################
### Extract CF contest status                                             ####
##############################################################################

def extract_submission_data():
    data = json.load(open(status_file))
    if data['status'] != 'OK':
        print(data)
        sys.exit(1)
    data = data['result'] # list of submissions
    return data

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

# GLOBAL
raw_submissions = extract_submission_data()

raw_submissions = list(filter(lambda s: s['author']['participantType'] == 'CONTESTANT',
                         raw_submissions))

##############################################################################
### Extract teams list                                                    ####
##############################################################################

def extract_team_list():
    ### teams :: teamId -> (teamName, members)
    teams = dict()

    individuals = dict()

    for sub in raw_submissions:
        author = sub['author']
        members = list(map(lambda u: u['handle'], author['members']))

        if 'teamId' not in author:
            if members[0] not in individuals:
                i = len(individuals)
                individuals[members[0]] = i
            i = individuals[members[0]]
            author['teamId'] = 10**6 + i
            author['teamName'] = members[0]

        team = author['teamId']
        teamName = author['teamName']
        teams[team] = (teamName, members)

    return teams

# GLOBAL
teams = extract_team_list()

##############################################################################
### Produce contest feed (xml)                                            ####
### Spec: https://clics.ecs.baylor.edu/index.php?title=Event_Feed_2016    ####
##############################################################################

contest_feed = ET.Element('contest')

def xadd(parent, child_name, child_text = None):
    child = ET.SubElement(parent, child_name)
    if child_text is not None:
        child.text = str(child_text)
    return child

### Info
contest_info = xadd(contest_feed, 'info')
xadd(contest_info, 'contest-id', '100')
xadd(contest_info, 'length', contest_details['length'])
xadd(contest_info, 'scoreboard-freeze-length', '01:00:00')
xadd(contest_info, 'penalty', '20')
xadd(contest_info, 'started', 'True')
xadd(contest_info, 'starttime', contest_details['startTimeSeconds'])
xadd(contest_info, 'title', contest_details['name'])
xadd(contest_info, 'short-title', contest_details['name'])

### Add only one language, and extract everything to that
lang = xadd(contest_feed, 'language')
xadd(lang, 'id', '1')
xadd(lang, 'name', 'C++')

### Contest regions - use it to form different contestant prize groups.
for i, name in enumerate(config.regions):
    reg = xadd(contest_feed, 'region')
    xadd(reg, 'external-id', i)
    xadd(reg, 'name', name)

### Possible verdicts: OK, WRONG (subsume everything into WRONG)
for verdict in ['OK', 'WRONG']:
    j = xadd(contest_feed, 'judgement')
    xadd(j, 'acronym', verdict)
    xadd(j, 'name', verdict)

### Problems:
for (pcode, pname) in problems:
    p = xadd(contest_feed, 'problem')
    xadd(p, 'id', problem_ids[pcode])
    xadd(p, 'label', pcode)
    xadd(p, 'name', pname)
    xadd(p, 'test_data_count', 1) # to suppress warnings

### Teams:
for teamId, teamData in teams.items():
    teamName, members = teamData

    t = xadd(contest_feed, 'team')
    xadd(t, 'id', teamId)
    xadd(t, 'name', teamName)
    xadd(t, 'nationality', 'India')
    xadd(t, 'university', 'IIIT Hyderabad')
    xadd(t, 'university-short-name', 'IIITH')
    # xadd(t, 'region', config.regions[0])

    ### TODO: figure out where to add member info
    # xadd(t, 'display_name', teamName + ' (' + ', '.join(members) + ')')

### Submission data:
submission_ignore_count = 0
for sub in raw_submissions:
    if 'verdict' not in sub or sub['verdict'] == 'COMPILATION_ERROR':
        submission_ignore_count += 1
        continue

    s = xadd(contest_feed, 'run')

    xadd(s, 'id', sub['id'])
    xadd(s, 'team', sub['author']['teamId'])
    xadd(s, 'judged', True)
    xadd(s, 'language', 'C++')
    xadd(s, 'problem', problem_ids[sub['problem']['index']])

    verdict = 'OK' if sub['verdict'] == 'OK' else 'WRONG'
    xadd(s, 'result', verdict)
    xadd(s, 'solved', verdict == 'OK')
    xadd(s, 'penalty', verdict != 'OK')

    xadd(s, 'time', sub['relativeTimeSeconds'])
    xadd(s, 'timestamp', sub['creationTimeSeconds'])

print('Total number of submissions:', len(raw_submissions))
print('> Submissions ignored', submission_ignore_count)

### Finalize!
(gold, silver, bronze) = config.medal_counts(len(teams))

finalized = xadd(contest_feed, 'finalized')
xadd(finalized, 'timestamp', time.time())
xadd(finalized, 'last-gold', gold)
xadd(finalized, 'last-silver', gold + silver)
xadd(finalized, 'last-bronze', gold + silver + bronze)

ET.indent(contest_feed)
ET.ElementTree(contest_feed).write(output_file)

print(f'Contest {config.contest_id} feed generated! Wrote to {output_file}')
