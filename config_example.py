api_key = 'YOUR CF API KEY HERE'
secret = 'YOUR CF API SECRET KEY'

# ID of cf contest
contest_id = '331059'
# first one is default region; cannot be empty
regions = ['IIIT', 'UG1', 'UG2']

def medal_counts(num_teams):
    k = (num_teams + 14) // 15
    return (k, k, k)
