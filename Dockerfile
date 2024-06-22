FROM python:3.9

WORKDIR /app

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y git

COPY .git /app/.git
RUN git --git-dir=/app/.git rev-parse HEAD > COMMIT_HASH && \
    rm -rf /app/.git

COPY docdepot.py /app/docdepot.py
COPY helper.py /app/helper.py
COPY docdepotdb.py /app/docdepotdb.py
COPY templates /app/templates
COPY ddclient /app/ddclient
COPY requirements.txt /app/requirements.txt

ENV DEPOSER_API_KEY='test'
RUN pip install pipreqs && pip install -r requirements.txt && chmod -R +x /app

EXPOSE 5000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["sh", "-c", "/app/entrypoint.sh"]
