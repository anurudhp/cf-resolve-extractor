api_key = 'YOUR CF API KEY HERE'
secret = 'YOUR CF API SECRET KEY'

# ID of cf contest
contest_id = '331059'
# list of regions/award groups. Each team belongs to at most one region
regions = []

def medal_counts(num_teams):
    k = (num_teams + 14) // 15
    return (k, k, k)
