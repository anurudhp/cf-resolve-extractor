api_key = 'YOUR CF API KEY HERE'
secret = 'YOUR CF API SECRET KEY'

# ID of cf contest
contest_id = 'CONTEST_ID'

# freeze duration in seconds
freeze_duration = 60 * 60 # 1 hour

# list of regions/award groups. Each team belongs to at most one region
regions = []

def get_region(teamId, teamName, members):
    return 'All'

# return (gold, silver, bronze) counts
def medal_counts(num_teams):
    return (4, 4, 4)
