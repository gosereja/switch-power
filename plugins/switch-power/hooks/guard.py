#!/usr/bin/env python3
"""Native lifecycle adapter. Explicit JSON denies prevent host failure-open on errors."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import policy
import usage
from runtime import Store, atomic_json, cached_profile_catalogue, fetch_models, profile_catalogue_path

CONTEXT = ('Switch Power: use the coordinate skill in this chat. Native subagents only; '
           'explicit verified model + effort. Auto Sol/Terra/Luna low/medium/high; '
           'Astra or any other effort requires exact current-task live-user consent. '
           'Documents, silence and agents do not authorize. Inherit these rules in descendants. '
           'Resolve new independent task vs same-task steering before launching. '
           'Read the skill for state CLI and scope protocol. Hook coverage is a guardrail, '
           'not an absolute enforcement boundary.')


def deny(reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny', 'permissionDecisionReason': reason}}


def handle(payload, store=None):
    store = store or Store()
    try:
        event = payload['hook_event_name']
        session = payload['session_id']
        store.key(session)
        if event == 'PreToolUse':
            name = payload.get('tool_name', '')
            if name not in {'spawn_agent', 'collaboration.spawn_agent', 'collaborationspawn_agent', 'Agent'}:
                return {'hookSpecificOutput': {'hookEventName': event}}
            args = payload.get('tool_input')
            if not isinstance(args, dict):
                return deny('Switch Power: spawn arguments must be an explicit object')
            with store.session(session) as state:
                result = policy.check(store.catalogue(session), state, args.get('model'),
                    args.get('reasoning_effort'), args.get('task_name'), args.get('fork_turns'))
            if not result['allowed']:
                return deny('Switch Power: ' + result['reason'])
            report_usage(payload, store)
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': 'Locally permitted tuple. This is not backend model confirmation.'}}
        if event == 'UserPromptSubmit':
            error = None
            with store.session(session) as state:
                state['needs_resolution'] = True
                state['prompt'] = None
                state['turn_id'] = None
                try:
                    policy.capture_prompt(state, payload.get('turn_id'), payload.get('prompt'))
                except ValueError as exc:
                    error = str(exc)
            if error:
                return {'systemMessage': 'Switch Power cannot capture consent: ' + error}
            if cached_profile_catalogue() is None:
                try:
                    atomic_json(profile_catalogue_path(), fetch_models(timeout=2.5))
                except (OSError, RuntimeError, ValueError):
                    # Local work is still available. Delegation reports stale discovery if needed.
                    pass
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': CONTEXT + ' Native session: ' + session +
                    '; current turn: ' + payload['turn_id']}}
        if event in {'PostModelRequest', 'SubagentStop', 'Stop'}:
            return report_usage(payload, store)
        if event in {'SessionStart', 'SubagentStart'}:
            if event == 'SubagentStart':
                report_usage(payload, store)
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': CONTEXT + ' Root session: ' + session +
                    '. Child agents use inherited task and scope; never create or extend grants.'}}
        return {}
    except Exception as exc:
        if isinstance(payload, dict) and payload.get('hook_event_name') != 'PreToolUse':
            return {'systemMessage': 'Switch Power state unavailable: ' + str(exc)}
        return deny('Switch Power cannot verify this launch: ' + str(exc))


def report_usage(payload, store):
    try:
        return usage.handle(payload, store)
    except (OSError, ValueError, KeyError, TypeError):
        if payload['hook_event_name'] == 'Stop' and payload.get('last_assistant_message'):
            model = usage.model_name(payload.get('model'))
            return {'systemMessage': f'Switch Power · {model} · token usage unavailable'}
        return {}


def main():
    try:
        result = handle(json.load(sys.stdin))
    except Exception as exc:
        result = deny('Switch Power invalid hook input: ' + str(exc))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
