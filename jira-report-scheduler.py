#!/usr/bin/env python3

"""
Copyright 2025 Dustin Black

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
import os
import subprocess
import yaml
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

parser = ArgumentParser(
    description="Scheduler from YAML for jira-report-runner.py",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "-i",
    "--input",
    type=str,
    dest="input_path",
    required=True,
    help=(
        "The absolute path to the YAML input file -- This is passed to the cron job, "
        "so a relative path will not work."
    )
)

args = parser.parse_args()

def run_cmd(command_list, cmd_input=None):
    #FIXME - Initialize cmd_out in case of OSError
    cmd_out = ""
    try:
        cmd_out = subprocess.run(
            command_list,
            capture_output=True,
            input=cmd_input,
            text=True,
            check=False,
        )
    except subprocess.CalledProcessError as err:
        print(f"{err.cmd[0]} failed with return code {err.returncode}:\n{err.output}")
        sys.exit(1)
    #FIXME -- Listing or removing a crontab that doesn't exist results in "OSError: [Errno 9] Bad file descriptor"
    except OSError:
        pass
    return "completed", cmd_out

try:
    with open (args.input_path, "r") as stream:
        jobs = yaml.safe_load(stream)
except:
    print("Error reading input file!")
    sys.exit(1)

# Clear the crontab
print("Removing existing crontab...")
list_cmd = run_cmd(["crontab", "-l"])
print(list_cmd[1].stdout)
clear_cmd = run_cmd(["crontab", "-r"])

print("Updating crontab...")

new_crontab = ""

for var in (
    "jira_server",
    "jira_token",
    "email_server",
    "email_from",
    "email_user",
    "email_token"
):
    try:
        new_crontab += f"{var}={os.environ[var]}\n"
    except KeyError:
        pass

# Self-updater schedule
new_crontab += "0 * * * * /usr/bin/startup.sh >/proc/1/fd/1 2>&1 \n"

for job in jobs["jira_report_jobs"]:
    job_id = job["job_id"]
    cron_schedule = job["cron_schedule"]
    cron_job = (
        f"{cron_schedule} jira-report-runner.py -j {job_id} -i "
        f"{args.input_path} >/proc/1/fd/1 2>&1\n"
    )
    new_crontab += cron_job

create_cmd = run_cmd(["crontab", "-"], cmd_input=new_crontab)
print(create_cmd[1].stdout)
