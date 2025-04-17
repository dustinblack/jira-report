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
    help="The path to the YAML input file"
)

args = parser.parse_args()

def run_cmd(command_list, cmd_stdin=None, cmd_stdout=subprocess.STDOUT, cmd_stderr=subprocess.STDOUT):
    try:
        cmd_out = subprocess.run(
            command_list,
            capture_output=True,
            stdin=cmd_stdin,
            stdout=cmd_stdout,
            stderr=cmd_stderr,
            text=True,
        )
    except subprocess.CalledProcessError as err:
        print(f"{err.cmd[0]} failed with return code {err.returncode}:\n{err.output}")
        sys.exit(1)
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
print list_cmd[1]
clear_cmd = run_cmd(["crontab", "-r"])

print("Updating crontab...")
for job in jobs["jira_report_jobs"]:
  job_id = job["job_id"]
  cron_schedule = job["cron_schedule"]
  run_cmd(
    [
      "echo",
      cron_schedule,
      "jira-report-runner.py",
      "-S",
      TODO,
      "-T",
      TODO,
      "-e",
      TODO,
      "-f",
      TODO,
      "-u",
      TODO,
      "-w",
      TODO,
      "-j",
      job_id,
      "-i",
      args.input_path
    ],
    cmd_stdout=subprocess.PIPE,
    cmd_stderr=None,
  )
  
  create_cmd = run_cmd(["crontab", "-"], stdin=subprocess.PIPE)
  print(create_cmd)
