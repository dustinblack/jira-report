#!/usr/bin/env python3

from argparse import ArgumentParser
from jira import JIRA
from logger import logger
import sys
from time import mktime
from datetime import datetime

parser = ArgumentParser(description="Status report generator from Jira query")

parser.add_argument(
    "--server", "-S", 
    type=str, 
    dest="jira_server", 
    required=True, 
    help="Jira server URL"
)
parser.add_argument(
    "--token", "-T", 
    type=str, 
    dest="jira_token", 
    required=True, 
    help="Jira authentication token"
)
parser.add_argument(
    "--jql", "-J", 
    type=str, 
    dest="jql", 
    required=True, 
    help="JQL query for Jira search"
)
parser.add_argument(
    "--recipients", "-r", 
    type=str, 
    dest="recipients", 
    required=False, 
    help="Comma-separated list of email addresses to receive report"
)
parser.add_argument(
    "--email-server", "-e", 
    type=str, 
    dest="email_server", 
    required=False, 
    help="Email SMTP server URL"
)
parser.add_argument(
    "--email-from", "-f", 
    type=str, 
    dest="email_from", 
    required=False, 
    help="Email address to send from"
)
parser.add_argument(
    "--email-subject", "-s", 
    type=str, 
    dest="email_subject", 
    required=False, 
    help="Email subject line"
)
parser.add_argument(
    "--email-message", "-m", 
    type=str, 
    dest="email_message", 
    required=False,
    default="",
    help="Email message to insert above query results"
)
parser.add_argument(
    "--local", "-l", 
    action="store_true",
    dest="local", 
    required=False, 
    default=False, 
    help="Do not send emails; only output the report locally (defaults to True if --recipients is empty)"
)

args = parser.parse_args()

if args.recipients and (args.email_server is None or args.email_from is None or args.email_subject is None) and not args.local:
    parser.error("--recipients requires --email_server, --email_from, and --email_subject")

logger.info(f"Connecting to Jira server: {args.jira_server}")

jira_conn = JIRA(server=args.jira_server, token_auth=(args.jira_token))

logger.info(f"Running Jira query with JQL: {args.jql}")

issues = []

try:
    issues.append(
        jira_conn.search_issues(
            jql_str=args.jql, 
            json_result=True, 
            maxResults=100, 
            expand='changelog', 
            fields = ['comment', 'assignee', 'creator', 'status', 'updated', 'summary']
        )
    )
except:
    logger.error("Jira query error!")
    sys.exit()

report_list = []

if issues[0]['total'] > 0:
    logger.info(f"Issue count: {issues[0]['total']}")
    for issue in issues:
        for result in issue['issues']:
            # logger.info(result)
            if result['fields']['assignee'] is None:
                owner = "NO OWNER"
            else:
                owner = result['fields']['assignee']['displayName']
            if len(result['fields']['comment']['comments']) > 0:
                latest_comment = result['fields']['comment']['comments'][-1]['body']
            else:
                latest_comment = "None"
            updated_time = datetime.strptime(result['fields']['updated'], "%Y-%m-%dT%H:%M:%S.%f%z")
            report_list.append({
                
                "issue" : result['key'],
                "link" : f"{args.jira_server}/browse/{result['key']}",
                "owner" : owner,
                "summary" : result['fields']['summary'],
                "creator" : result['fields']['creator']['displayName'],
                "status" : result['fields']['status']['name'],
                "updated" : datetime.strftime(updated_time, '%a %d %b %Y, %I:%M%p'),
                # "ID" : result['id'],
                "comment" : latest_comment,
            }) 
else:
    logger.warning("Query returned no results!")

report = []

for item in report_list:
    report.append(
        f"Issue #: {item['issue']} ({item['link']})\n"
        f"Owner: {item['owner']}\n"
        f"Summary: {item['summary']}\n"
        f"Updated: {item['updated']}\n"
        f"Latest update:\n{item['comment']}\n"
        "\n\n"
    )

report_message = ' '.join(report)

if args.recipients and not args.local:
    email_body = f"{args.email_message}\n\n{report_message}"
    logger.info(f"Emailing recipients: {args.recipients}")
    logger.info(f"Emailing from: {args.email_from}")
    logger.info(f"Email subject: {args.email_subject}")
    logger.info(f"Email message:\n{email_body}")
    #TODO implement SMTP message
    
else:
    logger.info("Email disabled; Printing query results locally only...\n")
    print(report_message)