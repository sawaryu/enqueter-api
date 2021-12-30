FROM python:3.9.6

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Timezone
ENV TZ="Asia/Tokyo"

# The filename executing application
ENV FLASK_APP=app

# Important description
COPY . /app

# Importtant variables getting from AWS SSM
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

# When executeing db migration, override the entry-CMD in the container definiton.
CMD ["uwsgi", "--ini", "app.ini"]