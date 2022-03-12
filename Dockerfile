FROM python:3.9.6-buster as builder

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
  && pip install -r requirements.txt

FROM python:3.9.6-slim-buster as runner

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin/uwsgi /usr/local/bin/uwsgi
COPY --from=builder /usr/local/bin/flask /usr/local/bin/flask

RUN apt update \
  && apt install -y libpq5 libxml2 \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY . /app

ARG SECRET_KEY
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_DEFAULT_REGION
ARG AWS_BUCKET_NAME
ARG AWS_PATH_KEY
ARG SQLALCHEMY_DATABASE_URI
ARG MAILGUN_API_KEY
ARG MAILGUN_DOMAIN_NAME
ARG FRONT_URL

ENV SECRET_KEY=${SECRET_KEY}
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
ENV AWS_BUCKET_NAME=${AWS_BUCKET_NAME}
ENV AWS_PATH_KEY=${AWS_PATH_KEY}
ENV SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI}
ENV MAILGUN_API_KEY=${MAILGUN_API_KEY}
ENV MAILGUN_DOMAIN_NAME=${MAILGUN_DOMAIN_NAME}
ENV FRONT_URL=${FRONT_URL}

ENV FLASK_APP=app
ENV TZ="Asia/Tokyo"
ENV FLASK_ENV="production"

WORKDIR /app
CMD ["uwsgi", "--ini", "app.ini"]