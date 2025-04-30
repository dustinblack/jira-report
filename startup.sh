#!/bin/bash

target=/jira-report-subscription
git clone $subscription_repo $target
cd $target
git fetch
git pull

/usr/sbin/crond -n -s