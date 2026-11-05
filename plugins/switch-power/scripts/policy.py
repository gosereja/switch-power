"""Local routing policy. This module never executes agents or authenticates users."""
from __future__ import annotations

import hashlib
import re
import time
import uuid

AUTO_EFFORTS = {'low', 'medium', 'high'}
MAX_CATALOGUE_AGE = 86400


def family(model):
    match = re.fullmatch(r'gpt-\d+(?:\.\d+)*-(sol|terra|luna|astra)', model or '')
    return match.group(1) if match else 'other'


def available(catalogue, model, effort, now=None):
    now = time.time() if now is None else now
    age = now - catalogue.get('fetched_at', 0)
    if age < -60 or age > MAX_CATALOGUE_AGE:
        raise ValueError('Catalogue expired or timestamp is invalid; refresh native model/list')
    rows = [m for m in catalogue.get('data', []) if m.get('model') == model]
    if len(rows) != 1:
        raise ValueError('Model missing or ambiguous in native catalogue: ' + str(model))
    if model not in catalogue.get('spawn_models', []):
        raise ValueError('Model absent from current native spawn allowlist: ' + str(model))
    supported = {v['reasoningEffort'] for v in rows[0].get('supportedReasoningEfforts', [])}
    if effort not in supported or effort not in catalogue.get('spawn_efforts', []):
        raise ValueError('Reasoning effort unsupported by catalogue or spawn schema: ' + str(effort))
    return rows[0]


def new_task(description):
    if not isinstance(description, str) or not description.strip():
        raise ValueError('A concrete independent task description is required')
    return {'task_id': uuid.uuid4().hex[:12], 'description': description,
            'scopes': {}, 'grants': [], 'failures': [], 'pending': None,
            'needs_resolution': False, 'turn_id': None, 'prompt': None, 'prompt_task_id': None}


def capture_prompt(state, turn_id, prompt):
    if not isinstance(turn_id, str) or not turn_id or not isinstance(prompt, str):
        raise ValueError('Native user prompt requires turn_id and text')
    state.update(turn_id=turn_id, prompt=prompt, needs_resolution=True, prompt_task_id=None)


def continue_task(state):
    if not state.get('task_id'):
        raise ValueError('No task to continue')
    state['needs_resolution'] = False
    state['prompt_task_id'] = state['task_id']


def add_scope(state, scope, description):
    if not re.fullmatch(r'[a-z0-9_]{1,48}', scope or '') or not description.strip():
        raise ValueError('Scope needs an ASCII id and concrete description')
    previous = state['scopes'].get(scope)
    if previous is not None and previous != description:
        raise ValueError('Scope descriptions are immutable; create a new scope')
    state['scopes'][scope] = description
    return f"sp_{state['task_id']}__{scope}"


def grant(state, model, effort, scope, source, turn_id, quote):
    """Record coordinator-classified consent, tied to an actual hook-captured prompt.

    Source is a coordinator assertion, not cryptographic provenance. The skill
    must classify intent; matching an excerpt does not prove semantic consent.
    """
    if state.get('needs_resolution') or not state.get('task_id'):
        raise ValueError('Resolve the independent-task boundary before recording consent')
    if source != 'live_user':
        raise ValueError('Only explicit live-user consent can authorize restricted launches')
    if turn_id != state.get('turn_id') or not turn_id:
        raise ValueError('Consent must refer to the current captured native user turn')
    if state.get('prompt_task_id') != state['task_id']:
        raise ValueError('Captured user permission is not bound to this task')
    if not isinstance(quote, str) or not quote.strip() or quote not in (state.get('prompt') or ''):
        raise ValueError('Verbatim explicit consent must occur in the captured live user prompt')
    if scope not in state.get('scopes', {}):
        raise ValueError('Unknown work scope')
    pending = state.get('pending')
    # Short answers only refer to a specific previously presented proposal.
    if quote.strip().lower() in {'да', 'yes', 'ок', 'ok', 'согласен', 'согласна'}:
        if not pending or any(pending[k] != v for k, v in
                              [('model', model), ('effort', effort), ('scope', scope)]):
            raise ValueError('A short approval needs the exact pending proposal')
        if pending.get('turn_id') == turn_id:
            raise ValueError('A proposal cannot be accepted before a later user turn')
    item = {'task_id': state['task_id'], 'model': model, 'effort': effort,
            'scope': scope, 'source_turn': turn_id,
            'evidence_sha256': hashlib.sha256(quote.encode()).hexdigest()}
    if item not in state['grants']:
        state['grants'].append(item)
    state['pending'] = None
    return item


def propose(state, model, effort, scope, reason):
    if scope not in state['scopes'] or not reason.strip():
        raise ValueError('Proposal requires a registered scope and concrete reason')
    state['pending'] = {'model': model, 'effort': effort, 'scope': scope,
                        'reason': reason, 'turn_id': state.get('turn_id')}
    return dict(state['pending'], work=state['scopes'][scope])


def check(catalogue, state, model, effort, task_name, fork_turns, now=None):
    try:
        available(catalogue, model, effort, now)
        if fork_turns != 'none':
            raise ValueError('Explicit overrides require verified isolated fork_turns=none')
        if not state.get('task_id') or state.get('needs_resolution'):
            raise ValueError('Resolve task boundary using task --new or task --continue first')
        prefix = f"sp_{state['task_id']}__"
        if not isinstance(task_name, str) or not task_name.startswith(prefix):
            raise ValueError('Task name must carry the current task id and registered scope')
        scope = task_name[len(prefix):]
        if scope not in state.get('scopes', {}):
            raise ValueError('Work scope is not registered')
        if any(f['model'] == model and f['effort'] == effort and f['scope'] == scope
               for f in state.get('failures', [])):
            raise ValueError('This tuple already failed in this scope; choose a permitted fallback')
        auto = family(model) in {'sol', 'terra', 'luna'} and effort in AUTO_EFFORTS
        permitted = any(g['task_id'] == state['task_id'] and g['model'] == model and
                        g['effort'] == effort and g['scope'] == scope
                        for g in state.get('grants', []))
        if not auto and not permitted:
            raise ValueError(f'Explicit prior user consent required for {model}/{effort}, scope {scope}')
        return {'allowed': True, 'model': model, 'reasoning_effort': effort,
                'scope': scope, 'status': 'policy_permitted_not_launched'}
    except (ValueError, KeyError, TypeError) as exc:
        return {'allowed': False, 'reason': str(exc), 'status': 'not_launched'}


def mark_failed(state, model, effort, scope, reason):
    state['failures'].append({'model': model, 'effort': effort, 'scope': scope,
                              'reason': reason})


def upgrade(catalogue, current):
    """Resolve vendor-provided upgrade pointers, without inventing/sorting IDs."""
    rows = {m['model']: m for m in catalogue.get('data', [])}
    if current not in rows or family(current) != 'sol':
        raise ValueError('Current coordinator must be a catalogue Sol model')
    row = rows[current]
    target = (row.get('upgradeInfo') or {}).get('model') or row.get('upgrade')
    if not target:
        return None
    if target not in rows or family(target) != 'sol' or target == current:
        raise ValueError('Vendor upgrade target is missing or is not another Sol')
    if 'high' not in {v['reasoningEffort'] for v in rows[target]['supportedReasoningEfforts']}:
        raise ValueError('Vendor target does not support high')
    return target


def recommend(catalogue, kind, complexity, ambiguity, priority, now=None):
    """Rank all launchable entries, using live descriptions plus initial family priors.

    A recommendation is advisory. The coordinator must inspect tool requirements
    and current official capability guidance before committing to the choice.
    """
    effort = 'high' if max(complexity, ambiguity) >= 3 else ('medium' if max(complexity, ambiguity) >= 1 else 'low')
    candidates = []
    for row in catalogue.get('data', []):
        model = row.get('model')
        try:
            available(catalogue, model, effort, now)
        except ValueError:
            continue
        f = family(model)
        score = 0
        text = row.get('description', '').lower()
        keywords = {'visual': ('visual', 'computer', 'screen'),
                    'code': ('code', 'coding', 'software'),
                    'analysis': ('reason', 'analysis', 'complex'),
                    'narrow': ('focused', 'efficient', 'volume')}.get(kind, ())
        score += sum(2 for word in keywords if word in text)
        if kind == 'visual' and f == 'terra':
            score += 3
        if kind == 'narrow' and f == 'luna':
            score += 3
        if max(complexity, ambiguity) >= 3 and f == 'sol':
            score += 3
        if priority == 'quality' and max(complexity, ambiguity) >= 3 and f == 'astra':
            score += 4
        if priority in {'speed', 'limits'} and f == 'luna':
            score += 2
        restricted = f not in {'sol', 'terra', 'luna'} or effort not in AUTO_EFFORTS
        candidates.append({'model': model, 'reasoning_effort': effort, 'score': score,
                           'description': row.get('description', ''),
                           'requires_consent': restricted, 'status': 'recommendation_only'})
    return sorted(candidates, key=lambda c: (-c['score'], c['requires_consent'], c['model']))
