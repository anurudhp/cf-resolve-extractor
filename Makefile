feed.xml: extract-cf.py status.json standings.json config.py
	python extract-cf.py status.json standings.json feed.xml

validate: feed.xml
	../contestUtil/eventFeed.sh --validate feed.xml

