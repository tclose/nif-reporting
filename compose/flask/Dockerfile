FROM debian:stretch-slim

LABEL maintainer="Tom Close <tom.g.close@gmail.com>"

# Copy Python requirements files
COPY ./requirements.txt /requirements.txt

# Add packages and install all dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN echo "deb http://http.debian.net/debian/ buster main contrib non-free" > /etc/apt/sources.list && \
  apt-get update && apt-get install -y \
    apt-transport-https \
    build-essential \
    cmake \
    curl \
    gcc \
    fontconfig \
    libc-dev \
    libffi-dev \
    libgdk-pixbuf2.0-0 \
    libjpeg-dev \
    musl-dev \
    ttf-mscorefonts-installer \
    patch \
    python3-cffi \
    python3-dev \
    python3-pip \
    shared-mime-info \
    sqlite \
    sssd-common \
    tzdata \
    unixodbc-dev \
    vim \
    zlib1g-dev && \
  pip3 install --no-cache-dir \
    gunicorn==19.7.1 \
    -r /requirements.txt && \
  gem install --no-document \
    listen && \
  fc-cache -f


# Install required locales (MS SQL Server requires US locale)
RUN apt-get install -y locales \
    && echo "en_AU.UTF-8 UTF-8" > /etc/locale.gen \
    && echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen

#  Set timezone
ARG TIMEZONE
RUN ln -snf /usr/share/zoneinfo/$TIMEZONE /etc/localtime && \
    echo $TIMEZONE > /etc/timezone

# Add config.py to container to configure the app
COPY ./compose/app/config.py config.py

# Set up 'app' user and add to sudoers
ARG APP_USER_ID
RUN addgroup --system --gid $APP_USER_ID app && \
    adduser --uid $APP_USER_ID --system app

EXPOSE 8000

# Work user and environment
USER app

# Move to root of the container and add it to the PATH
ENV PATH "$PATH:/:/scripts"
ENV PYTHONPATH /
WORKDIR /
