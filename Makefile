feed.json: extract-cf.py status.json standings.json config.py
	python extract-cf.py status.json standings.json feed.json

validate: feed.json
	../contestUtil/eventFeed.sh --validate feed.json

