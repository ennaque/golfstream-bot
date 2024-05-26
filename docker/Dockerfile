FROM python:3.11

RUN apt update && apt install -y npm gettext sqlite3 libsqlite3-dev libpq-dev binutils libproj-dev gdal-bin

WORKDIR /usr/src/app
RUN apt update && apt -y --no-install-recommends install fish

COPY . .

RUN pip install -r /usr/src/app/requirements.txt