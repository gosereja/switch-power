#!/usr/bin/env python3
"""Native lifecycle adapter. Explicit JSON denies prevent host failure-open on errors."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import policy
from runtime import Store

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
            if name not in {'spawn_agent', 'collaboration.spawn_agent', 'Agent'}:
                return {'hookSpecificOutput': {'hookEventName': event}}
            args = payload.get('tool_input')
            if not isinstance(args, dict):
                return deny('Switch Power: spawn arguments must be an explicit object')
            with store.session(session) as state:
                result = policy.check(store.catalogue(session), state, args.get('model'),
                    args.get('reasoning_effort'), args.get('task_name'), args.get('fork_turns'))
            if not result['allowed']:
                return deny('Switch Power: ' + result['reason'])
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
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': CONTEXT + ' Native session: ' + session +
                    '; current turn: ' + payload['turn_id']}}
        if event in {'SessionStart', 'SubagentStart'}:
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': CONTEXT + ' Root session: ' + session +
                    '. Child agents use inherited task and scope; never create or extend grants.'}}
        return {}
    except Exception as exc:
        if isinstance(payload, dict) and payload.get('hook_event_name') != 'PreToolUse':
            return {'systemMessage': 'Switch Power state unavailable: ' + str(exc)}
        return deny('Switch Power cannot verify this launch: ' + str(exc))


def main():
    try:
        result = handle(json.load(sys.stdin))
    except Exception as exc:
        result = deny('Switch Power invalid hook input: ' + str(exc))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
