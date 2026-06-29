ARG BUILD_FROM
FROM $BUILD_FROM

COPY app /app/app
COPY run.sh /
RUN chmod a+x /run.sh

WORKDIR /app
CMD [ "/run.sh" ]
