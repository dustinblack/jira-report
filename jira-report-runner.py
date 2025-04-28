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
import subprocess
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import yaml

parser = ArgumentParser(
    description="Runner from YAML for jira-report.py",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

# Passed-through arguments
parser.add_argument(
    "-S",
    "--server",
    type=str,
    dest="jira_server",
    required=True,
    help="Full Jira server URL including https://",
)
parser.add_argument(
    "-T",
    "--token",
    type=str,
    dest="jira_token",
    required=True,
    help="Jira user authentication token; Create this in your Jira user profile",
)
parser.add_argument(
    "-e",
    "--email-server",
    type=str,
    dest="email_server",
    required=True,
    default="smtp.gmail.com",
    help="Email SMTP server URL (assumes SSL)",
)
# parser.add_argument(
#     "-p",
#     "--smtp-port",
#     type=int,
#     dest="smtp_port",
#     required=True,
#     default=465,
#     help="Email SMTP server port number",
# )
parser.add_argument(
    "-f",
    "--email-from",
    type=str,
    dest="email_from",
    required=False,
    help="Email address to send from if different from the the email user",
)
parser.add_argument(
    "-u",
    "--email-user",
    type=str,
    dest="email_user",
    required=True,
    help="Email user account address",
)
parser.add_argument(
    "-w",
    "--email-password",
    type=str,
    dest="email_password",
    required=True,
    help="Email password (make sure you use an app password!)",
)

# Runner arguments
parser.add_argument(
    "-j",
    "--job-id",
    type=str,
    dest="job_id",
    required=True,
    help="The job ID from the YAML input to run"
)
parser.add_argument(
    "-i",
    "--input",
    type=str,
    dest="input_path",
    required=True,
    help="The path to the YAML input file"
)

args = parser.parse_args()

try:
    with open (args.input_path, "r") as stream:
        jobs = yaml.safe_load(stream)
except:
    print("Error reading input file!")
    sys.exit(1)

print(jobs)

for job in jobs["jira_report_jobs"]:
    if args.job_id in job["job_id"]:
        myjob = job
        break

print(f"\n{myjob}")

cmd = [
        "jira-report.py",
        "-S",
        args.jira_server,
        "-T",
        args.jira_token,
        "-e",
        args.email_server,
        # "-p",
        # args.smtp_port,
        "-u",
        args.email_user,
        "-w",
        args.email_password,
        "-r",
        ",".join(myjob["email"]["recipients"]),
        "-s",
        myjob['email']['subject'],
        "-m",
        myjob['email']['message'],
        "-J",
        myjob['jql'],
        #TODO make optional
        "-x",
        ",".join(myjob["exclude_comment_authors"]),
        "-g",
        str(myjob["update_grace_days"]),
    ]

if args.email_from:
    cmd.append(
        "-f",
        args.email_from,
    )

print(f"\n{' '.join(cmd)}")

try:
    cmd_out = subprocess.check_output(
        cmd,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(f"Job completed:\n{cmd_out}")
except subprocess.CalledProcessError as err:
    print(
        f"{err.cmd[0]} failed with return code {err.returncode}:\n{err.output}"
    )
    sys.exit(1)
