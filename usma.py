from flask import Flask, render_template, url_for, jsonify
import requests as rq
import os


app = Flask(__name__)

JIRA_ADDR = 'https://' + os.environ['JIRA_ADDR']
JIRA_AUTH = (
    os.environ['JIRA_USER'],
    os.environ['JIRA_TOKEN']
)
BACKLOG_FILTER = os.environ['BACKLOG_FILTER']
FIELD_EPIC_LINK = os.environ['FIELD_EPIC_LINK']


@app.route("/")
def usma():
    # fetch actions
    actions = _fetch_actions()

    # fetch stories
    flat_actions = sum([sum(activities.values(), []) for activities in actions.itervalues()], [])
    stories = _fetch_stories(flat_actions)

    # assign stories to actions
    stories_per_action = {a['key']: [] for a in flat_actions}
    for s in stories:
        stories_per_action[s['epic']].append(s)

    return render_template('usma.html',
                           name='usma',
                           actions_model=actions,
                           stories_model=stories_per_action)


@app.route("/actions")
def fetch_actions():
    # fetch actions
    actions = _fetch_actions()

    # form the response
    return jsonify(actions)


@app.route("/stories")
def fetch_stories():
    # fetch actions
    actions = _fetch_actions()

    # fetch stories
    flat_actions = sum([sum(activities.values(), []) for activities in actions.itervalues()], [])
    stories = _fetch_stories(flat_actions)

    # assign stories to actions
    stories_per_action = {a['key']: [] for a in flat_actions}
    for s in stories:
        stories_per_action[s['epic']].append(s)

    # form the response
    return jsonify(stories_per_action)


with app.test_request_context():
    url_for("static", filename="usma.css")


def _fetch_stories(actions):
    # fetch data from Jira
    url = JIRA_ADDR + '/rest/api/2/search'
    action_keys = [a['key'] for a in actions]
    params = {
        'jql': 'filter=%s and "Epic Link" in (%s)' % (BACKLOG_FILTER, ','.join(action_keys)),
        'fieldsByKeys': 'true',
        'fields': 'status,summary,labels,%s' % FIELD_EPIC_LINK
    }
    r = rq.get(url, params=params, auth=JIRA_AUTH)
    assert r.status_code / 100 == 2, 'Failed to fetch issues: %d %s' % (r.status_code, r.text)
    stories = r.json()['issues']

    # transform
    stories = [_extract_issue(s) for s in stories]

    return stories


def _fetch_actions():
    # fetch data from Jira
    url = JIRA_ADDR + '/rest/api/2/search'
    params = {
        'jql': 'filter=%s and issuetype=epic and labels=USMA_ACTION' % BACKLOG_FILTER,
        'fieldsByKeys': 'true',
        'fields': 'status,summary,labels'
    }
    r = rq.get(url, params=params, auth=JIRA_AUTH)
    assert r.status_code / 100 == 2, 'Failed to fetch issues: %d %s' % (r.status_code, r.text)
    epics = r.json()['issues']

    # transform
    epics = [_extract_issue(e) for e in epics]
    personas = _extract_personas(sum([e['labels'] for e in epics], []))
    epics_per_persona = {p: {} for p in personas}
    for e in epics:
        # get persona
        pp = _extract_personas(e['labels'])
        assert len(pp) > 0, 'an action has no PERSONA attached. labels: ' + ','.join(e['labels'])

        # get activity
        aa = _extract_activities(e['labels'])
        assert len(aa) > 0, 'an action has no ACTIVITY attached. labels: ' + ','.join(e['labels'])

        # store it
        for p in pp:
            for a in aa:
                epics = epics_per_persona[p].get(a, [])
                epics_per_persona[p][a] = epics + [e]
    return epics_per_persona


def _extract_issue(issue):
    return {
        'key': issue['key'],
        'summary': issue['fields']['summary'],
        'status': issue['fields']['status']['name'],
        'labels': issue['fields']['labels'],
        'link': '%s/browse/%s' % (JIRA_ADDR, issue['key']),
        'epic': issue['fields'].get(FIELD_EPIC_LINK, None)
    }


def _get_persona(l):
    return l.split('USMA_PERSONA_')[-1] if 'USMA_PERSONA_' in l else None


def _get_activity(l):
    return l.split('USMA_ACTIVITY_')[-1] if 'USMA_ACTIVITY_' in l else None


def _extract_personas(labels):
    labels = [_get_persona(l) for l in labels]
    labels = set(labels)
    labels.remove(None)
    return labels


def _extract_activities(labels):
    labels = [_get_activity(l) for l in labels]
    labels = set(labels)
    labels.remove(None)
    return labels
