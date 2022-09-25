FROM python:3.8

ARG REMOTE_INDEX_AT
ENV REMOTE_INDEX_AT=${REMOTE_INDEX_AT}

RUN curl -s $REMOTE_INDEX_AT | tar -xz > whoosh_index

COPY requirements.txt requirements.txt
COPY src src
COPY setup.py setup.py

# install requires
RUN pip install -r requirements.txt

# go
CMD ["python", "-m", "app.wsgi"]
