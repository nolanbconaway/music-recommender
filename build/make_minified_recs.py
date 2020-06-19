"""Make a minified JSON payload of the recommendations.

This is suitable for use an an API where no data enrichment is needed (e.g., you don't
need artist names, title names). It is gzipped so that it is as small as possible.

Use like:

$ python -m build.make_minified_recs data.db mini.json.gz

Shouldn't take too long!
"""

import argparse
import gzip
import json
import sqlite3
from pathlib import Path

SQL = """
select
    group_id,
    group_concat(recommendation_group_id, ',') as recommendation_groups_str
from (
    select * 
    from recommendations 
    order by group_id, recommendation_number
) as t
group by 1
"""


def parse_args():
    """Parse CLI args."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "db_path", type=Path, help="Path to the location of the SQLite DB.",
    )
    p.add_argument(
        "gzip_path", type=Path, help="Path to save the gzipped data.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # get list of group IDs to insert
    print("Querying sqlite...")
    with sqlite3.connect(args.db_path) as conn:
        # stringified integer keys, tuple of integer values
        results = {
            str(r[0]): tuple(map(int, r[1].split(","))) for r in conn.execute(SQL)
        }

    print("Saving data...")
    with gzip.GzipFile(args.gzip_path, "w") as f:
        f.write(json.dumps(results).encode("utf-8"))
