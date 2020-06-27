FROM python:3.8

ARG WHOOSH_INDEX_DOWNLOAD_URL

COPY requirements.txt requirements.txt
COPY src src
COPY setup.py setup.py

# install requires
RUN pip install --no-cache-dir -r requirements.txt

# get the index in place. downloads via cURL, assumes you have a tar.gz ready to 
# download over http.
ENV WHOOSH_INDEX_DIR whoosh_index
RUN curl $WHOOSH_INDEX_DOWNLOAD_URL | tar -xz > whoosh_index

CMD [ "python", "-m", "app.wsgi" ]