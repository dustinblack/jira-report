#!/usr/bin/env python3

"""
Copyright 2023 Dustin Black

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

===

Work inspired by https://github.com/jtaleric/nudge/tree/5cc1be48a64646839bd2f5aa751ac7266da7b3c9

Copyright 2021 Joe Talerico

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

from argparse import ArgumentParser
from jira import JIRA
from logger import logger
import sys
from datetime import datetime
from smtplib import SMTP_SSL
from email.mime.text import MIMEText

# import pprint


parser = ArgumentParser(description="Status report generator from Jira query")

parser.add_argument(
    "--server",
    "-S",
    type=str,
    dest="jira_server",
    required=True,
    help="Jira server URL",
)
parser.add_argument(
    "--token",
    "-T",
    type=str,
    dest="jira_token",
    required=True,
    help="Jira authentication token",
)
parser.add_argument(
    "--jql", "-J", type=str, dest="jql", required=True, help="JQL query for Jira search"
)
parser.add_argument(
    "--recipients",
    "-r",
    type=str,
    dest="recipients",
    required=False,
    help="Comma-separated list of email addresses to receive report",
)
parser.add_argument(
    "--email-server",
    "-e",
    type=str,
    dest="email_server",
    required=False,
    help="Email SMTP server URL (assumes SSL)",
)
parser.add_argument(
    "--smtp-port",
    "-p",
    type=int,
    dest="smtp_port",
    required=False,
    default=465,
    help="Email SMTP server port number",
)
parser.add_argument(
    "--email-from",
    "-f",
    type=str,
    dest="email_from",
    required=False,
    help="Email address to send from",
)
parser.add_argument(
    "--email-user",
    "-u",
    type=str,
    dest="email_user",
    required=False,
    help="Email user address if different than email from address",
)
parser.add_argument(
    "--email-subject",
    "-s",
    type=str,
    dest="email_subject",
    required=False,
    help="Email subject line",
)
parser.add_argument(
    "--email-message",
    "-m",
    type=str,
    dest="email_message",
    required=False,
    default="",
    help="Email message to insert above query results",
)
parser.add_argument(
    "--email-password",
    "-w",
    type=str,
    dest="email_password",
    required=False,
    help="Email password (make sure you use an app password!)",
)
parser.add_argument(
    "--local",
    "-l",
    action="store_true",
    dest="local",
    required=False,
    default=False,
    help=(
        "Do not send emails; only output the report locally (defaults to True if"
        " --recipients is empty)"
    ),
)

args = parser.parse_args()

if (
    args.recipients
    and (
        args.email_server is None
        or args.email_from is None
        or args.email_subject is None
        or args.email_password is None
    )
    and not args.local
):
    parser.error(
        "--recipients requires --email-server, --email-from, --email-subject, and"
        " --email-password"
    )

if args.email_user is None:
    args.email_user = args.email_from


def send_email(subject, body, sender, user, recipients, password):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    smtp_server = SMTP_SSL(args.email_server, args.smtp_port)
    smtp_server.login(user, password)
    smtp_server.sendmail(sender, recipients, msg.as_string())
    smtp_server.quit()


logger.info(f"Connecting to Jira server: {args.jira_server}")

jira_conn = JIRA(server=args.jira_server, token_auth=(args.jira_token))

logger.info(f"Running Jira query with JQL: {args.jql}")

# test
# pp = pprint.PrettyPrinter(width=41, compact=True)
# pp.pprint(jira_conn.search_issues(jql_str=args.jql,json_result=True,maxResults=30))

issues = []

try:
    issues.append(
        jira_conn.search_issues(
            jql_str=args.jql,
            json_result=True,
            maxResults=100,
            fields=[
                "issuetype",
                "parent",
                "comment",
                "assignee",
                "creator",
                "status",
                "updated",
                "summary",
                "status",
                "customfield_12311140",
            ],
        )
    )
except:
    logger.error("Jira query error!")
    sys.exit()

report_list = []

if issues[0]["total"] > 0:
    issue_count = issues[0]["total"]
    logger.info(f"Issue count: {issue_count}")
    for issue in issues:
        for result in issue["issues"]:
            result_dict = {}
            subtask = None

            if result["fields"]["assignee"] is None:
                owner = "NO OWNER"
            else:
                owner = result["fields"]["assignee"]["displayName"]
            if len(result["fields"]["comment"]["comments"]) > 0:
                latest_comment = result["fields"]["comment"]["comments"][-1]["body"]
            else:
                latest_comment = "None"
            updated_time = datetime.strptime(
                result["fields"]["updated"], "%Y-%m-%dT%H:%M:%S.%f%z"
            )

            if result["fields"]["customfield_12311140"]:
                # Get the epic name based on the epic ID (customfield_12311140)
                epic_jql = f"issue = {result['fields']['customfield_12311140']}"
                try:
                    epic_search = jira_conn.search_issues(
                        jql_str=epic_jql,
                        json_result=True,
                        maxResults=1,
                        fields=["summary"],
                    )
                except:
                    logger.error("Jira query error!")
                    sys.exit()
                epic_number = f"{result['fields']['customfield_12311140']}"
                epic_summary = f"{epic_search['issues'][0]['fields']['summary']}"
                epic = f"{epic_number} - {epic_summary}"
            elif result["fields"]["issuetype"]["subtask"]:
                # Subtasks do not return epic IDs, so get it from the parent
                subtask_jql = f"issue = {result['fields']['parent']['key']}"
                try:
                    epic_search = jira_conn.search_issues(
                        jql_str=subtask_jql,
                        json_result=True,
                        maxResults=1,
                        fields=["summary", "customfield_12311140"],
                    )
                except:
                    logger.error("Jira query error!")
                    sys.exit()
                epic_number = (
                    f"{epic_search['issues'][0]['fields']['customfield_12311140']}"
                )
                epic_summary = f"{epic_search['issues'][0]['fields']['summary']}"
                epic = f"{epic_number} - {epic_summary}"
                subtask = f"This is a subtask of {result['fields']['parent']['key']}"
            else:
                # This should result in 'None'
                epic = result["fields"]["customfield_12311140"]

            result_dict["Issue"] = f"{result['key']} - {result['fields']['summary']}"
            result_dict["Link"] = f"{args.jira_server}/browse/{result['key']}"
            if subtask is not None:
                result_dict["Sub-Task"] = subtask
            result_dict["Owner"] = owner
            result_dict["Epic"] = epic
            result_dict["Epic Link"] = f"{args.jira_server}/browse/{epic_number}"
            result_dict["Status"] = result["fields"]["status"]["name"]
            result_dict["Updated"] = datetime.strftime(
                updated_time, "%a %d %b %Y, %I:%M%p"
            )
            result_dict["Latest Update"] = latest_comment

            report_list.append(result_dict)

else:
    logger.warning("Query returned no results!")

if args.recipients and not args.local:

    html_report = [f"Issue count: {issue_count}<br><br>\n"]

    for item in report_list:
        html_report.append("<hr>\n")

        for key, value in item.items():
            if "Link" in key:
                if "Epic" not in key:
                    link = value
                else:
                    epic_link = value

        for key, value in item.items():
            if "Link" not in key:
                if "Latest" not in key:
                    if "Issue" in key:
                        html_report.append(
                            f"<b>{key}</b>: <a href='{link}'>{value}</a><br>"
                        )
                    elif "Epic" in key:
                        if value and "subtask" not in value:
                            html_report.append(
                                f"<b>{key}</b>: <a href='{epic_link}'>{value}</a><br>"
                            )
                        else:
                            html_report.append(
                                f"<b>{key}</b>: <span style='color:red'>{value}</span><br>"
                            )
                    else:
                        html_report.append(f"<b>{key}</b>: {value}<br>\n")
                else:
                    html_report.append(f"<b>{key}</b>: <pre>{value}</pre><br>\n")
        html_report.append("\n\n")

    html_message = " ".join(html_report)

    email_body = f"{args.email_message}<br><br>{html_message}"
    recipients_list = args.recipients.split(",")

    logger.info(f"Emailing recipients: {args.recipients}")
    logger.info(f"Emailing from: {args.email_from}")
    logger.info(f"Email subject: {args.email_subject}")
    logger.info(f"Email message:\n{email_body}")

    send_email(
        args.email_subject,
        email_body,
        args.email_from,
        args.email_user,
        recipients_list,
        args.email_password,
    )

    logger.info("Email sent")

else:

    report = [f"Issue count: {issue_count}\n\n"]

    for item in report_list:
        report.append("==========\n")
        for key, value in item.items():
            if "Link" not in key:
                report.append(f"{key}: {value}\n")
            elif "Epic" in key and item["Epic"] and "subtask" not in item["Epic"]:
                report.append(f"({value})\n")
            elif "Epic" not in key:
                report.append(f"({value})\n")
        report.append("\n\n")

    report_message = " ".join(report)

    logger.info("Email disabled; Printing query results locally only...\n")
    print(report_message)
