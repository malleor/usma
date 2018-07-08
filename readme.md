# Prerequisites

Usma assumes you have `python`, `pip` and `make`.

# Building

```
make build
```

# Running

You will need a local config file `./app-env`:

```
export JIRA_ADDR="..."      # address of your JIRA
export JIRA_USER="..."      # your JIRA login
export JIRA_TOKEN="..."     # your personal JIRA API token
export BACKLOG_FILTER="..." # your board's JIRA filter ID
```

Then you run USMA, which will use the a/m file for config:

```
make run
```
