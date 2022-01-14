feed.xml: extract-cf.py status.json standings.json
	python extract-cf.py status.json standings.json feed.xml

validate: feed.xml
	../contestUtil/eventFeed.sh --validate feed.xml

