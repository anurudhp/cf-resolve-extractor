import sys, os.path, argparse
import time, datetime
import json
import sh
import xml.etree.ElementTree as ET

import config
from cfapi import APICall

import logging
logging.basicConfig(format='[%(levelname)s]: %(message)s', level=logging.DEBUG)

##############################################################################
### Helpers                                                               ####
##############################################################################
def epochToISO(s):
    return datetime.datetime.fromtimestamp(s).isoformat(timespec='milliseconds') + '+00'

def secondsToHHMMSS(s):
    res = str(datetime.timedelta(seconds = int(s))) + '.000'
    if res[1] == ':':
        res = '0' + res
    return res

##############################################################################
### Input                                                                 ####
##############################################################################
if len(sys.argv) < 4:
    print(f'Usage: python3 {sys.argv[0]} <status>.json <standings>.json <output>.json')
    sys.exit(1)

# GLOBAL
status_file = sys.argv[1]
standings_file = sys.argv[2]
output_file = sys.argv[3]

##############################################################################
### Query API if file isn't present                                       ####
##############################################################################

if not os.path.isfile(status_file):
    logging.info(f'Fetching status for {config.contest_id}...')
    call = APICall('contest.status', True)
    call.add('contestId', config.contest_id)
    call.add('from', 1)
    call.add('count', 5000)
    url = call.get_url()
    time.sleep(1)
    sh.wget(url, '-O', status_file)
    logging.info(f'Status fetched!')

if not os.path.isfile(standings_file):
    logging.info(f'Fetching standings for {config.contest_id}...')
    call = APICall('contest.standings', True)
    call.add('contestId', config.contest_id)
    call.add('from', 1)
    call.add('count', 1)
    url = call.get_url()
    time.sleep(1)
    sh.wget(url, '-O', standings_file)
    logging.info(f'Standings fetched!')

##############################################################################
### Extract CF contest problem list                                       ####
##############################################################################

def extract_problem_data():
    data = json.load(open(standings_file))
    assert(data['status'] == 'OK')
    data = data['result']

    contest_details = data['contest']
    length = data['contest']['durationSeconds']
    contest_details['length'] = '%02d:%02d:%02d.000' % (length//3600, (length/60)%60, length%60)

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
        logging.error('submission data not fetched')
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

_unique_event_index = 0
def create_event(typ, data, op):
    global _unique_event_index
    _unique_event_index += 1
    return {
        'type': typ,
        'id': f'icpc_event_{_unique_event_index}',
        'op': op,
        'data': data
    }

contest_events = []
def add_event(typ, data, op='create'):
    ev = create_event(typ, data, op)
    ev = json.dumps(ev)
    contest_events.append(ev)
    return ev

### Contest state update event
def show_contest_state(ended=False, done=False):
    tstart = contest_details['startTimeSeconds']
    tfin = tstart + contest_details['durationSeconds']
    tfrozen = tfin - config.freeze_duration
    tthaw = tfin + 300
    tdone = int(time.time())

    data = {
        'started': tstart,
        'ended': tfin if ended or done else None,
        'frozen': tfrozen,
        'thawed': tthaw,
        'finalized': tdone if done else None,
        'end_of_updates': tdone + 60 if done else None
    }
    for k in data.keys():
        if data[k] is not None:
            data[k] = epochToISO(data[k])

    if '_contest_state_shown' not in globals():
        global _contest_state_shown
        _contest_state_shown = False

    add_event('state', data, 'update' if _contest_state_shown else 'create')
    _contest_state_shown = True

### Info
add_event('contests', {
    'id': '100',
    "name": contest_details['name'],
    "formal_name": contest_details['name'],
    "start_time": epochToISO(contest_details['startTimeSeconds']),
    "duration": contest_details['length'],
    "scoreboard_freeze_duration": secondsToHHMMSS(config.freeze_duration),
    "penalty_time":20
})

### Add only one language, and extract everything to that
add_event("languages", {"id":"1", "name":"C++"})

### Contest regions - use it to form different contestant prize groups.
for i, name in enumerate(config.regions):
    add_event('groups',{"id":str(i),"icpc_id":str(i),"name":name})

### Possible verdicts: OK, WRONG (subsume everything into WRONG)
for verdict in ['OK', 'WRONG']:
    ok = verdict == 'OK'
    add_event('judgement-types', {
        "id": verdict,
        "name": verdict,
        "penalty": not ok,
        "solved": ok
    })

### Problems:
for (pcode, pname) in problems:
    add_event('problems', {
        "id": pcode,
        "label": pcode,
        "name": pname,
        "ordinal":problem_ids[pcode] - 1,
        "test_data_count": 1
    })

### Organizations
### TODO: add support for multiple orgs
add_event('organizations',{
    "id":"org_default",
    "icpc_id": None,
    "name": "Default",
    "formal_name":"Default",
    "country":"India"
})

### Teams:
for teamId, teamData in teams.items():
    teamName, members = teamData
    fullTeamName = teamName + ' (' + ', '.join(members) + ')'
    region = config.get_region(teamId, teamName, members)
    region = config.regions.index(region)

    add_event('teams', {
        "id": teamId,
        "name": fullTeamName,
        "group_ids":[str(region)],
        "organization_id": "org_default"
    })


### Submission data:
show_contest_state() # start the contest

submission_ignore_count = 0
for sub in raw_submissions:
    if 'verdict' not in sub or sub['verdict'] == 'COMPILATION_ERROR':
        submission_ignore_count += 1
        continue

    sub_id = str(sub['id'])
    verdict = 'OK' if sub['verdict'] == 'OK' else 'WRONG'
    timestamp = epochToISO(sub['creationTimeSeconds'])
    reltime = secondsToHHMMSS(sub['relativeTimeSeconds'])

    add_event('submissions', {
        'id': sub_id,
        "problem_id": sub['problem']['index'],
        "team_id": str(sub['author']['teamId']),
        "language_id": "1",
        "files": [],
        "contest_time":reltime,
        "time":timestamp
    })
    add_event('judgements', {
        'id': sub_id,
        "submission_id": sub_id,
        "judgement_type_id": verdict,
        "start_contest_time":reltime,
        "end_contest_time":reltime,
        "start_time":timestamp,
        "end_time":timestamp
    })

logging.info(f'Total number of submissions: {len(raw_submissions)}')
logging.info(f'Submissions ignored {submission_ignore_count}')

show_contest_state(done=True) # end the contest

### Generate UG1 data, used to extract first solved info.
'''sample format
{
    "type":"awards",
    "id":"icpc417",
    "op":"create",
    "data": {
        "id":"id-0.42676245053009976",
        "citation":"UG1: First to solve A",
        "team_ids":["86480"]
    }
}
'''
def generateUG1Awards():
    firstSolves = dict()
    firstSolveTime = dict()

    for sub in raw_submissions:
        if 'verdict' not in sub or sub['verdict'] != 'OK':
            continue
        team = str(sub['author']['teamId'])
        if str(team) not in config.ug1teams:
            continue
        prob = problem_ids[sub['problem']['index']]
        subtime = int(sub['relativeTimeSeconds'])

        if prob not in firstSolveTime:
            firstSolveTime[prob] = subtime
            firstSolves[prob] = []
        if firstSolveTime[prob] > subtime:
            firstSolves[prob] = []
        if firstSolveTime[prob] >= subtime:
            firstSolveTime[prob] = subtime
            firstSolves[prob].append(team)

    for prob, teams in firstSolves.items():
        add_event('awards', {
            'id': f'ug1_aux_award_{prob}_data',
            'citation': f'UG1 - First to solve problem {problems[prob-1][0]}',
            'team_ids': teams
        })
    logging.info(f'wrote {len(firstSolves)} UG1 awards')

generateUG1Awards()

logging.info(f'total events: {len(contest_events)}')
with open(output_file, 'w') as f:
    f.write('\n'.join(contest_events))
    f.write('\n')
logging.info(f'Contest {config.contest_id} feed generated! Wrote to {output_file}')
