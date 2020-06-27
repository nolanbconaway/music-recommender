"""Set up app config."""

import os
from pathlib import Path

from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser, OrGroup

WHOOSH_INDEX_DIR = Path(os.getenv("WHOOSH_INDEX_DIR", "whoosh_index"))
SEARCH_INDEX = open_dir(WHOOSH_INDEX_DIR)
QUERY_PARSER = MultifieldParser(
    ["name", "artist_name"], SEARCH_INDEX.schema, group=OrGroup.factory(0.9)
)
