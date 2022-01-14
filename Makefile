feed.xml: extract-cf.py status.json standings.json
	python extract-cf.py status.json standings.json feed.xml

validate: feed.xml
	touch feed.json
	mv feed.json feed.json.bak
	../contestUtil/eventFeed.sh --convert feed.xml feed.json
	../contestUtil/eventFeed.sh --validate feed.json

