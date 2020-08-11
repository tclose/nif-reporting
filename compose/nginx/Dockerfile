FROM nginx:1.12-alpine-perl

# Delete default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf 

# Set timezone and read site name from the environment variable into the 
# nginx.conf
ARG TIMEZONE
ARG HOSTNAME
ADD ./nginx.conf.template nginx.conf.template
RUN apk add --update --no-cache --virtual .build-deps \
        tzdata \
        gettext && \
    cp /usr/share/zoneinfo/$TIMEZONE /etc/localtime && \
    echo $TIMEZONE > /etc/timezone && \
    < nginx.conf.template envsubst '$HOSTNAME' \
    > /etc/nginx/nginx.conf && \
    apk del .build-deps gettext
