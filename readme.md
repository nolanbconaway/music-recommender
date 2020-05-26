# Redacted Recommender

This is a music recommender built on top of the RED user snatches API.

## Design

- `build/`: scripts to collect the data from the redacted API. In its final form it should produce a mapping between each album (group) ID and the album you'd recommend. Future iterations might consider providing recommendations on the basis of a multi-album reference set but lets keep it simple for now OK.
- `sample_data.json.gz`: gzipped sample raw data from `build.user_snatches`. The full JSON file is too big for github and I do not intend on dealing with LFS. This is the data to work with while developing an algorithm.

### Later

- `app/`: REST API serving the recommendations.
