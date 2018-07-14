from flask import Flask, render_template, url_for, jsonify
import requests as rq
import os
from simple_settings import settings


app = Flask(__name__)


@app.route("/storymap")
def storymap():
    # fetch actions
    actions = _fetch_actions()

    # fetch stories
    flat_actions = sum([sum(activities.values(), []) for activities in actions.itervalues()], [])
    stories = _fetch_stories(flat_actions)

    # assign stories to actions
    stories_per_action = {a['key']: [] for a in flat_actions}
    for s in stories:
        stories_per_action[s['epic']].append(s)

    # break down stories by actions and milestones
    milestones = list(set(sum([s['milestones'] for s in stories], []))) + [None]
    stories_per_action = {a['key']: {m: [] for m in milestones} for a in flat_actions}
    for s in stories:
        if len(s['milestones']) == 0:
            stories_per_action[s['epic']][None].append(s)
        else:
            for m in s['milestones']:
                stories_per_action[s['epic']][m].append(s)

    # force milestones order, based on settings
    if settings.MILESTONES:
        milestones = settings.MILESTONES + [m for m in milestones if m not in settings.MILESTONES]

    # prep persona icons
    persona_images = { p: settings.PERSONA_IMAGES.get(p, 'static/generic-user.png')
                       for p in actions.keys() }

    return render_template('storymap.html',
                           name='usma',
                           actions_model=actions,
                           stories_model=stories_per_action,
                           milestones=milestones,
                           persona_images=persona_images)


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

    # break down stories by actions and milestones
    milestones = list(set(sum([s['milestones'] for s in stories], [])))
    stories_per_action = {a['key']: {m: [] for m in milestones + [None]} for a in flat_actions}
    for s in stories:
        if len(s['milestones']) == 0:
            stories_per_action[s['epic']][None].append(s)
        else:
            for m in s['milestones']:
                stories_per_action[s['epic']][m].append(s)

    # form the response
    return jsonify(stories_per_action)


@app.route("/roadmap")
def roadmap():
    # fetch actions
    actions = _fetch_actions()

    # fetch stories
    flat_actions = sum([sum(activities.values(), []) for activities in actions.itervalues()], [])
    stories = _fetch_stories(flat_actions)

    # break down stories by actions and milestones
    milestones = list(set(sum([s['milestones'] for s in stories], [])))
    stories_breakdown = {m: {a['key']: [] for a in flat_actions} for m in milestones + [None]}
    for s in stories:
        if len(s['milestones']) == 0:
            stories_breakdown[None][s['epic']].append(s)
        else:
            for m in s['milestones']:
                stories_breakdown[m][s['epic']].append(s)
    if settings.MILESTONES:
        milestones = settings.MILESTONES + [m for m in milestones if m not in settings.MILESTONES]
    actions_by_key = {a['key']: a['summary'] for a in flat_actions}
    unassigned_actions = [actions_by_key[a] for a in stories_breakdown[None].keys()]
    stories_breakdown = [
        (m, {a: {
                    'summary': actions_by_key[a],
                    'done': (len([1 for s in stories if s['status'] == 'Done'])*100. / len(stories)) if len(stories) > 0 else 0,
                    'inprogress': (len([1 for s in stories if s['status'] == 'In Progress'])*100. / len(stories)) if len(stories) > 0 else 0,
                    'stories': stories
                }
             for a, stories in stories_breakdown[m].iteritems() if len(stories) > 0})
        for m in milestones
    ]

    return render_template('roadmap.html',
                           milestones=stories_breakdown,
                           unassigned_actions=unassigned_actions)
    # return jsonify(stories_breakdown)


with app.test_request_context():
    url_for("static", filename="usma.css")


def _fetch_stories(actions):
    # fetch data from Jira
    url = settings.JIRA_ADDR + '/rest/api/2/search'
    action_keys = [a['key'] for a in actions]
    params = {
        'jql': 'filter=%s and "Epic Link" in (%s) order by rank' % (settings.BACKLOG_FILTER, ','.join(action_keys)),
        'fieldsByKeys': 'true',
        'fields': 'status,summary,labels,%s,fixVersions' % settings.FIELD_EPIC_LINK
    }
    r = rq.get(url, params=params, auth=settings.JIRA_AUTH)
    assert r.status_code / 100 == 2, 'Failed to fetch issues: %d %s' % (r.status_code, r.text)
    stories = r.json()['issues']

    # transform
    stories = [_extract_issue(s) for s in stories]

    return stories


def _fetch_actions():
    # fetch data from Jira
    url = settings.JIRA_ADDR + '/rest/api/2/search'
    params = {
        'jql': 'filter=%s and issuetype=epic and labels=USMA_ACTION order by rank' % settings.BACKLOG_FILTER,
        'fieldsByKeys': 'true',
        'fields': 'status,summary,labels'
    }
    r = rq.get(url, params=params, auth=settings.JIRA_AUTH)
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
        'link': '%s/browse/%s' % (settings.JIRA_ADDR, issue['key']),
        'epic': issue['fields'].get(settings.FIELD_EPIC_LINK, None),
        'milestones': [v['name'] for v in issue['fields'].get('fixVersions', [])]
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
