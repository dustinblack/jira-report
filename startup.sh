#!/bin/bash

target=/jira-report-subscription
git clone $subscription_repo $target
cd $target
git fetch
git pull

/usr/bin/jira-report-scheduler.py -i ${target}/subscriptions.yaml

/usr/sbin/crond -n -s