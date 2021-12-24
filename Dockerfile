FROM python:3.9.6

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# timezone
ENV TZ="Asia/Tokyo"

# filename of executing application
ENV FLASK_APP=app

# important description
COPY . /app

# importtant variables from AWS SSM
ENV FLASK_CONFIGURATION="production"

ARG SECRET_KEY
ENV SECRET_KEY=${SECRET_KEY}

ARG AWS_ACCESS_KEY_ID
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ARG AWS_SECRET_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV AWS_REGION="ap-northeast-1"
ENV AWS_BUCKET_NAME="mainmybucket"
ENV AWS_PATH_KEY="avatar/"

ARG SQLALCHEMY_DATABASE_URI
ENV SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI}

# If execute db migration, override the entry-CMD in the container definiton.
CMD ["uwsgi", "--ini", "app.ini"]