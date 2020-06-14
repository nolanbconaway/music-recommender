# Data Build

This directory contains a python module with tools to build the production dataset as a batch process. This process as it stands takes multiple days to run and is not at all very good. It consists of:

1. `user_snatches.py`. Scrape data from the site's web API. This takes many hours as there is a two-second timeout between requests. 50k users at two-seconds each (the very best case scenario) is ~28 hours. More realistically it will take twice as long. Data are saved to a JSON file with one user's data per line.
2. `make_sqlite.py`. Build a temporary sqlite database off the JSON data from the previous step. This takes just a few minutes.
3. `make_recommendations.py`. Add a recommendations mapping table to the temporary sqlite database from the previous step. This is split out as a separate step because it takes several hours.
4. `to_production.py`. Export data from the sqlite database to a production MySQL database. This should take no more than a few minutes.

All the above scripts are built with a CLI, so from the parent directory of this repository you can call them like

```sh
python -m build.<script> -h
```

