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

===

Work inspired by:
 https://github.com/jtaleric/nudge/tree/5cc1be48a64646839bd2f5aa751ac7266da7b3c9

Copyright 2021 Joe Talerico
"""

import sys
import pprint
from requests import post
from datetime import datetime
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from jira import JIRA, JIRAError
from logger import logger



parser = ArgumentParser(
    description="Status report generator from Jira query",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

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
    "-J",
    "--jql",
    type=str,
    dest="jql",
    required=True,
    help="JQL query for Jira search",
)
parser.add_argument(
    "-r",
    "--recipients",
    type=str,
    dest="recipients",
    required=False,
    help="Comma-separated list of email addresses to receive report",
)
parser.add_argument(
    "-e",
    "--email-server",
    type=str,
    dest="email_server",
    required=False,
    default="smtp.gmail.com",
    help="Email SMTP server URL (assumes SSL)",
)
parser.add_argument(
    "-p",
    "--smtp-port",
    type=int,
    dest="smtp_port",
    required=False,
    default=465,
    help="Email SMTP server port number",
)
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
    "-s",
    "--email-subject",
    type=str,
    dest="email_subject",
    required=False,
    help="Email subject line",
)
parser.add_argument(
    "-m",
    "--email-message",
    type=str,
    dest="email_message",
    required=False,
    default="",
    help="Email message to insert above query results",
)
parser.add_argument(
    "-w",
    "--email-password",
    type=str,
    dest="email_password",
    required=False,
    help="Email password (make sure you use an app password!)",
)
parser.add_argument(
    "-L",
    "--llm-model-api",
    type=str,
    dest="llm_model_api",
    required=False,
    help="API endpoint for LLM model to use for AI summaries",
)
parser.add_argument(
    "-I",
    "--llm-model-id",
    type=str,
    dest="llm_model_id",
    required=False,
    help="ID of the LLM model to use for AI summaries",
)
parser.add_argument(
    "-K",
    "--llm-token",
    type=str,
    dest="llm_token",
    required=False,
    help="Authentication token for the LLM API",
)
parser.add_argument(
    "-x",
    "--exclude-comment-author",
    type=str,
    dest="author_filter",
    required=False,
    default="bot",
    help=(
        "Comments by authors that include this text will be skipped"
    ),
)
parser.add_argument(
    "-g",
    "--update-grace-days",
    type=str,
    dest="update_grace_days",
    required=False,
    default=10,
    help=(
        "Grace period in days for issue updates before highlighting them in red in"
        " the HTML report"
    ),
)
parser.add_argument(
    "-l",
    "--local",
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

if args.email_from is None:
    args.email_from = args.email_user


def send_email(subject, body, sender, user, recipients, password):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    smtp_server = SMTP_SSL(args.email_server, args.smtp_port)
    smtp_server.login(user, password)
    smtp_server.sendmail(sender, recipients, msg.as_string())
    smtp_server.quit()


def llm_helper(
    query: str,
    model_api=args.llm_model_api,
    model_id=args.llm_model_id,
    token=args.llm_token,
):
    print("Following the white rabbit...")

    message_header = (
        "== AI SUMMARY ==\n"
        f"Model used: {model_id}\n"
        "Warning: AI-generated summaries may contain inaccuracies. Users must verify "
        "all information before use.\n\n"
    )

    message_footer = "== END AI SUMMARY ==\n\n"

    url = f"{model_api.rstrip('/')}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    messages = [
        {
            "role": "user",
            "content": query
        }
    ]

    data = {"model": model_id, "messages": messages, "temperature": 0.7}

    try:
        response = post(url, headers=headers, json=data, timeout=30, verify=False)
        response.raise_for_status()
        response_data = response.json()

        assistant_message = response_data["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_message})

        return message_header + assistant_message + "\n\n" + message_footer

    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, "response") and hasattr(e.response, "text"):
            print(f"Response: {e.response.text}")


logger.info(f"Connecting to Jira server: {args.jira_server}")

jira_conn = JIRA(server=args.jira_server, token_auth=(args.jira_token))

logger.info(f"Running Jira query with JQL: {args.jql}")

# debug
pp = pprint.PrettyPrinter(width=41, compact=True)
# pp.pprint(jira_conn.search_issues(jql_str=args.jql,json_result=True,maxResults=30))

issues = []

# Build the array of issues from the JQL query
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
except JIRAError as error:
    logger.error(f"Jira query error:\n{error}")
    sys.exit(1)

# debug
# pp.pprint(issues)
# exit()

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

            all_comments = []
            if len(result["fields"]["comment"]["comments"]) > 0:
                for comment in result["fields"]["comment"]["comments"]:
                    if args.author_filter in comment["author"]["name"]:
                        continue
                    all_comments.append(comment["body"])
                comment_number = -1
                try:
                    while (
                        args.author_filter
                        in result["fields"]["comment"]["comments"][comment_number][
                            "author"
                        ]["name"]
                    ):
                        comment_number -= 1
                        # debug
                        # print(f'Skipped comment: {result["fields"]["comment"]["comments"][comment_number]["body"]}')
                    latest_comment = result["fields"]["comment"]["comments"][
                        comment_number
                    ]["body"]
                except IndexError:
                    latest_comment = "None (filtered)"
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
                except JIRAError as error:
                    logger.error(f"Jira query error:\n{error}")
                    sys.exit(1)
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
                except JIRAError as error:
                    logger.error(f"Jira query error:\n{error}")
                    sys.exit(1)
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
            result_dict["All Comments"] = "\n".join(all_comments)

            report_list.append(result_dict)

else:
    logger.error("Query returned no results!")
    sys.exit(1)

# Always generate the html report so that we can use it for the llm
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
        if "All Comments" in key:
            continue
        if "Link" not in key:
            if "Latest" not in key:
                if "Issue" in key:
                    html_report.append(
                        f"<b>{key}</b>: <a href='{link}'>{value}</a><br>"
                    )
                elif "Epic" in key:
                    if value:
                        html_report.append(
                            f"<b>{key}</b>: <a href='{epic_link}'>{value}</a><br>"
                        )
                    else:
                        html_report.append(
                            f"<b>{key}</b>: <span style='color:red'>{value}</span><br>"
                        )
                elif "Updated" in key:
                    updated_datetime = datetime.strptime(
                        value, "%a %d %b %Y, %I:%M%p"
                    )
                    delta = datetime.now() - updated_datetime
                    if delta.days >= int(args.update_grace_days):
                        html_report.append(
                            f"<b>{key}</b>: <span style='color:red'>{value}</span><br>"
                        )
                    else:
                        html_report.append(f"<b>{key}</b>: {value}<br>")
                else:
                    html_report.append(f"<b>{key}</b>: {value}<br>\n")
            else:
                html_report.append(f"<b>{key}</b>: <pre>{value}</pre><br>\n")
    html_report.append("\n\n")

html_message = " ".join(html_report)


## LLM Playground
llm_summary = ""
if args.llm_model_api and args.llm_model_id and args.llm_token:

    llm_report = [f"Issue count: {issue_count}\n\n"]

    for item in report_list:
        llm_report.append("==========\n")
        for key, value in item.items():
            if "Link" not in key:
                llm_report.append(f"{key}: {value}\n")
            elif "Epic" in key and item["Epic"] and "subtask" not in item["Epic"]:
                llm_report.append(f"({value})\n")
            elif "Epic" not in key:
                llm_report.append(f"({value})\n")
        llm_report.append("\n\n")

    llm_report_message = " ".join(llm_report)

    llm_summary = llm_helper(
        query = (
            "In your response, do not use gendered pronouns when referring to a "
            "person. "

            "Any URLs in your output should be formatted as hyperlinks with HTML. "

            "In a section titled 'Priority Attention Needed', note each issue that "
            "does not have an assigned Epic or that has an Updated date older than "
            f"{args.update_grace_days} and note why each issue needs attention. "

            "In another section titled 'Current Work', use no more than three "
            "sentences per owner to describe narratively in third person what each "
            "owner is working on, highlighting any potential risks or blockers. "

            "In a third section titled 'Recently Closed Issues', note each issue that "
            f"has been closed in the last {args.update_grace_days}, based on "
            "the issue's 'Status' field, along with the outcomes of the work. "

            "In a final section titled 'Productivity and Efficiency Suggestions', in "
            "the context of this content, offer suggestions to improve productivity or "
            "efficiency. These suggestions should not be generic ideas that may be "
            "considered obvious. Use this content for the request: "
            f"\n{llm_report_message}"
        ),
        model_api=args.llm_model_api,
        model_id=args.llm_model_id,
        token=args.llm_token,
    )

if args.recipients and not args.local:
    email_body = f"{args.email_message}<br><br>"
    if llm_summary:
        email_body += f"<pre>{llm_summary}</pre>"
    email_body += html_message
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
    print(f"{llm_summary}\n")
    report = [f"Issue count: {issue_count}\n\n"]

    for item in report_list:
        report.append("==========\n")
        for key, value in item.items():
            if "All Comments" in key:
                continue
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
