CF 'ICPC Resolver' Helper
-------------------------

Helper to extract CF contest data into ICPC resolver format.

Requirements
------------

Go to [tools.icpc.global](https://tools.icpc.global/) and download "Resolver".
Optionally you can download "Contest Utilities" to validate the generated files.

In Resolver, you should have the executables `resolver.sh` and `awards.sh`
In Contest Utilites, you should have the executable `eventFeed.sh` (others are not needed).

Usage
-----

1. Copy `config-example.py` to `config.py` and set the parameters in it.
1. Run `python3 extract-cf.py <status_file>.json <standings_file>.json <output>.xml`
  - `<status_file>.json`: File to take submission info from (will fetch using API if not found)
  - `<standings_file>.json`: File to take contest info from (will fetch using API if not found)
  - `<output>.xml`: File to write the contest feed to.
1. Run the resolver with `/path/to/resolver.sh output.xml`
1. (optinal) To validate, run `/path/to/eventFeed.sh --validate output.xml`.
1. (optional) To edit the awards manually, run `/path/to/awards.sh`. Select "Disk" and load the generated `output.xml` file.


