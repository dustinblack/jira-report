ARG CONTAINER_BASE="centos:stream9"

FROM $CONTAINER_BASE

COPY jira-report.py /usr/bin/jira-report.py
COPY requirements.txt /requirements.txt

RUN python3 -m ensurepip \
    && pip3 install -r requirements.txt

ENTRYPOINT ["/usr/bin/jira-report.py"]