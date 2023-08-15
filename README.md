# jira-report
Generates a status report for issues based on a Jira JQL query. All input parameters are passed as command flags.

By default, the command expects to **generate an HTML email and send it via an SMTP server** using SSL with authentication.

Missing Epic links and update dates older than a grace period (by default 10 days) will be ${\textsf{\color{red}highlighted\ in\ red}}$ in the HTML report.

Passing the `--local / -l` flag will generate a local text-only report.



Sample output (with `-l`):
```
Issue count: 32

 ==========
 Issue: JIRA-1712
 (https://jira.url/browse/JIRA-1712)
 Owner: John Doe
 Epic: JIRA-1008
 (https://jira.url/browse/JIRA-1008)
 Summary: Lorem ipsum dolor sit amet
 Status: Closed
 Updated: Thu 15 Sep 2022, 01:43PM
 Latest Update: Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
 

 ==========
 Issue: JIRA-2154
 (https://jira.url/browse/JIRA-2154)
 Owner: Jane Smith
 Epic: JIRA-2092
 (https://jira.url/browse/JIRA-2092)
 Summary: Duis aute irure dolor in reprehenderit in voluptate velit esse
 Status: In Progress
 Updated: Tue 02 May 2023, 09:06PM
 Latest Update: Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
```

## Command syntax
```
$ ./jira-report.py -h
usage: jira-report.py [-h] --server JIRA_SERVER --token JIRA_TOKEN --jql JQL [--recipients RECIPIENTS] [--email-server EMAIL_SERVER] [--smtp-port SMTP_PORT] [--email-from EMAIL_FROM] [--email-user EMAIL_USER]
                      [--email-subject EMAIL_SUBJECT] [--email-message EMAIL_MESSAGE] [--email-password EMAIL_PASSWORD] [--local]

Status report generator from Jira query

optional arguments:
  -h, --help            show this help message and exit
  --server JIRA_SERVER, -S JIRA_SERVER
                        Jira server URL
  --token JIRA_TOKEN, -T JIRA_TOKEN
                        Jira authentication token
  --jql JQL, -J JQL     JQL query for Jira search
  --recipients RECIPIENTS, -r RECIPIENTS
                        Comma-separated list of email addresses to receive report
  --email-server EMAIL_SERVER, -e EMAIL_SERVER
                        Email SMTP server URL (assumes SSL)
  --smtp-port SMTP_PORT, -p SMTP_PORT
                        Email SMTP server port number
  --email-from EMAIL_FROM, -f EMAIL_FROM
                        Email address to send from
  --email-user EMAIL_USER, -u EMAIL_USER
                        Email user address if different than email from address
  --email-subject EMAIL_SUBJECT, -s EMAIL_SUBJECT
                        Email subject line
  --email-message EMAIL_MESSAGE, -m EMAIL_MESSAGE
                        Email message to insert above query results
  --email-password EMAIL_PASSWORD, -w EMAIL_PASSWORD
                        Email password (make sure you use an app password!)
  --local, -l           Do not send emails; only output the report locally (defaults to True if --recipients is empty)
```

***Treat these items with care as they provide access to your accounts with your credentials***
- **`JIRA_TOKEN`** - In your Jira profile, create a *Personal Access Token*. This is the token used by the script.
- **`EMAIL_PASSWORD`** - Assuming Gmail, you will need to create an *App Password* for your Google account and use that here.

## GitHub Actions Automated Reports
The [.github/workflows/report.yaml](.github/workflows/report.yaml) file provides automation to run this script directly from GitHub Actions. The configuration provided here runs the script as a scheduled cron job. Parameters are passed to the script using GitHub Actions Secrets for this repo, which provide for automatic masking of the information in the script output. You will need to define these secrets and adjust the script as appropriate for your needs.