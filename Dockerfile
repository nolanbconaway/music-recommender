FROM python:3.8

# set up whoosh index. later, set this up to grab from a variable.
RUN curl http://nolanc.heliohost.org/whoosh_index.tar.gz | tar -xz > whoosh_index

COPY requirements.txt requirements.txt
COPY src src
COPY setup.py setup.py

# install requires
RUN pip install -r requirements.txt

# go
CMD ["python", "-m", "app.wsgi"]
