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
import re
import datetime
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import yaml

env_vars = {}
for var in (
    "jira_server",
    "jira_token",
    "email_server",
    "email_from",
    "email_user",
    "email_token"
):
    try:
        env_vars[var] = os.environ[var]
    except KeyError:
        env_vars[var] = ""

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
    required=False,
    default=env_vars["jira_server"],
    help="Full Jira server URL including https://",
)
parser.add_argument(
    "-T",
    "--token",
    type=str,
    dest="jira_token",
    required=False,
    default=env_vars["jira_token"],
    help="Jira user authentication token; Create this in your Jira user profile",
)
parser.add_argument(
    "-e",
    "--email-server",
    type=str,
    dest="email_server",
    required=False,
    default=env_vars["email_server"],
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
    default=env_vars["email_from"],
    help="Email address to send from if different from the the email user",
)
parser.add_argument(
    "-u",
    "--email-user",
    type=str,
    dest="email_user",
    required=False,
    default=env_vars["email_user"],
    help="Email user account address",
)
parser.add_argument(
    "-w",
    "--email-password",
    type=str,
    dest="email_password",
    required=False,
    default=env_vars["email_token"],
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

for job in jobs["jira_report_jobs"]:
    if args.job_id in job["job_id"]:
        myjob = job
        break

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
        "-J",
        myjob['jql'],
        #TODO make optional
        "-x",
        ",".join(myjob["exclude_comment_authors"]),
        "-g",
        str(myjob["update_grace_days"]),
    ]

# Get and format any date parematers from the subject and message body
date_param_re = re.compile(r"^(.*)(\$\(date *(?:\+[\"\'][^\"\']+[\"\'])?\))(.*)$")
date_format_re = re.compile(r"^\$\(date *(?:\+[\"\']([^\"\']+)[\"\'])?\)$")
now = datetime.datetime.now()
for opt in (["-s", "subject"], ["-m", "message"]):
    param_re_match = date_param_re.match(myjob["email"][opt[1]])
    if param_re_match:
        msg_str = ""
        for group in param_re_match.groups():
            fomat_re_match = date_format_re.match(str(group))
            if fomat_re_match:
                    if fomat_re_match.groups()[0]:
                        msg_str += now.strftime(str(fomat_re_match.groups()[0]))
                    else:
                        msg_str += now.strftime("%a %b %e %r %Z %Y")
            else:
                msg_str += str(group)
    else:
        msg_str = str(myjob["email"][opt[1]])
    cmd.extend([
        opt[0],
        msg_str,
    ])

if args.email_from:
    cmd.extend([
        "-f",
        args.email_from,
    ])

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
