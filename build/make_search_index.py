"""Create a whoosh search index from the minified JSON.

Use like:

$ python -m build.make_search_index mini.json.gz .whoosh_index

Adding files should take a minute or two, commiting it all should take another few 
minutes. On one run it took my machine 8 mins.
"""

import argparse
import sqlite3
from pathlib import Path

import tqdm
from whoosh.fields import NUMERIC, TEXT, Schema
from whoosh.index import create_in

# produces a schema like: group_id, artist_name, name, recommendations_str
# with recommendations_str as a comma delimited string of group ints.
#
# one could split and then integer the groups and then map back to the index.
SQL = """
with g as (
    select
        group_id,
        artists.name as artist_name,
        groups.name
    from groups
    inner join artists on groups.artist_id = artists.artist_id
),

r as (
    select
        group_id,
        group_concat(recommendation_group_id, ',') as recommendations_str
    from (select * from recommendations order by group_id, recommendation_number) as t
    group by 1
)

select
   g.group_id, 
   artist_name, 
   name, 
   recommendations_str

from g 
left join r 
  on g.group_id = r.group_id
"""


def parse_args():
    """Parse CLI args."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    p.add_argument(
        "db_path", type=Path, help="Path to the sqlite data.",
    )
    p.add_argument(
        "index_path", type=Path, help="Path to save the index data.",
    )
    p.add_argument(
        "--memory", type=int, default=256, help="Memory limit (mb) for indexing.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.index_path.exists():
        args.index_path.mkdir()

    # storing EVERYTHIGN because the whole thing is running on this index.
    schema = Schema(
        group_id=NUMERIC(stored=True),
        name=TEXT(stored=True),
        artist_name=TEXT(stored=True),
        recommendations_str=TEXT(stored=True),
    )
    search_index = create_in(args.index_path, schema)

    with sqlite3.connect(args.db_path) as conn, search_index.writer(
        limitmb=args.memory, multisegment=True
    ) as writer:

        n = conn.execute("select count(*) from groups").fetchall()[0][0]
        res = conn.execute(SQL)

        for group_id, artist_name, name, recommendations_str in tqdm.tqdm(res, total=n):
            writer.add_document(
                group_id=group_id,
                artist_name=artist_name,
                name=name,
                recommendations_str=recommendations_str,
            )
