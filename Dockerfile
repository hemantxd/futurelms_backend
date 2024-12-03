FROM python:3.9.10

ENV APP_HOME /code
ENV PYTHONPATH $APP_HOME
ENV PYTHONUNBUFFERED 1
ENV ENV_CONFIG 1
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

COPY requirements.txt $APP_HOME/requirements.txt
RUN pip install -r requirements.txt

RUN set -e && \
  pip install --upgrade pip && \
  pip install --no-cache-dir uwsgi

COPY . $APP_HOME 

EXPOSE 8000

ENV UWSGI_WSGI_FILE=./config/wsgi.py

ENV UWSGI_HTTP=:8000 UWSGI_MASTER=1 UWSGI_HTTP_AUTO_CHUNKED=1 UWSGI_HTTP_KEEPALIVE=1 UWSGI_LAZY_APPS=1 UWSGI_WSGI_ENV_BEHAVIOR=holy

ENV UWSGI_WORKERS=2 UWSGI_THREADS=4

RUN python manage.py migrate --noinput

CMD NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program python manage.py runserver 0.0.0.0:8000

