"""Record observed native model attempts and render one post-answer notice."""
import re
import time

from policy import ASTRA_TRIAL, SAMPLE_MAX_AGE, family

TOKEN_FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens',
                'reasoning_output_tokens', 'total_tokens')


def model_name(value):
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}', value):
        return value
    return 'unknown model'


def track_scope(state, task_id, scope, turn, bucket):
    route = state.get('route')
    if route and route['task_id'] == task_id:
        if (route['scope'], route['bucket']) != (scope, bucket):
            raise ValueError('Track one comparable routing scope per task')
        return
    state['route'] = {'task_id': task_id, 'scope': scope, 'first_turn': turn, 'bucket': bucket}


def mark_outcome(state, task_id, scope, turn, verified):
    route = state.get('route')
    if not route or (route['task_id'], route['scope']) != (task_id, scope):
        raise ValueError('Outcome requires the tracked routing scope')
    if state.get('turn') != turn or state.get('reported'):
        raise ValueError('Record the routing outcome during the current turn, before Stop')
    route['outcome'] = {'turn': turn, 'verified': verified}


def add_counts(phases, phase, counts):
    current = phases.setdefault(phase, {field: 0 for field in TOKEN_FIELDS})
    for field in TOKEN_FIELDS:
        value = counts.get(field)
        if current[field] is None or type(value) is not int or value < 0:
            current[field] = None
        else:
            current[field] += value


def save_route(state, store, incomplete):
    route = state.get('route')
    if not route or route.get('closed'):
        return
    turn = state['turn']
    coordinators = state.get('coordinators', {})
    coordinator = next(iter(coordinators), '')
    phases = state.get('phases', {})
    complete = (not incomplete and len(coordinators) == 1 and family(coordinator) == 'sol'
                and 'setup' in phases)
    solo = state['launches'] == 0 and not state['workers']
    if turn == route.get('proposal_turn'):
        if complete and solo:
            route['proposal'] = phases['setup']
            route['coordinator'] = coordinator
        else:
            route['closed'] = True
        return
    continuing_trial = ('proposal' in route and route['coordinator'] == coordinator
                        and route.get('continued_turn') == turn)
    outcome = route.get('outcome', {})
    if complete and solo and continuing_trial and outcome.get('turn') != turn:
        add_counts(route, 'clarification', phases['setup'])
        return
    route['closed'] = True
    if not complete or outcome.get('turn') != turn:
        return
    if 'proposal_turn' not in route and turn == route['first_turn'] and solo:
        label = 'sol'
    elif (continuing_trial and state['launches'] == len(state['workers']) == 1
          and state.get('measured_launch') == f"sp_{route['task_id']}__{route['scope']}"
          and list(state.get('worker_models', {})) == [ASTRA_TRIAL[0]]
          and {'worker', 'verification'} <= phases.keys()):
        label = 'astra'
        phases = dict(phases, proposal=route['proposal'])
        if 'clarification' in route:
            phases['clarification'] = route['clarification']
    else:
        return
    now = time.time()
    sample = dict(phases, task_id=route['task_id'], bucket=route['bucket'],
                  route=label, coordinator=coordinator, verified=outcome['verified'],
                  recorded_at=now, total_tokens=sum(p['total_tokens'] for p in phases.values()))
    with store.routing_history() as history:
        samples = [r for r in history.get('samples', [])
                   if now - r['recorded_at'] <= SAMPLE_MAX_AGE and r['task_id'] != route['task_id']]
        history['samples'] = (samples + [sample])[-512:]


def handle(payload, store):
    event = payload['hook_event_name']
    turn = payload.get('turn_id')
    if not isinstance(turn, str) or not turn:
        return {}
    agent = payload.get('agent_id')
    model = model_name(payload.get('model'))
    with store.usage(payload['session_id']) as state:
        if event == 'PostModelRequest' and not agent and turn != state.get('turn'):
            previous_workers = {key: worker['id'] for key, worker in state.get('workers', {}).items()}
            route = state.get('route')
            state.clear()
            state.update(turn=turn, workers={}, models={}, total=0, seen=0, launches=0,
                         partial=False, reported=False, previous_workers=previous_workers,
                         phases={}, coordinators={}, worker_models={})
            if route:
                state['route'] = route
        if event == 'Stop' and state.get('turn') != turn and payload.get('last_assistant_message'):
            state.clear()
            state.update(turn=turn, reported=True)
            return {'systemMessage': f'Switch Power · {model} · token usage unavailable'}
        if not state.get('turn') or state.get('reported'):
            return {}

        workers = state['workers']
        if event == 'SubagentStart' and agent:
            workers.setdefault(turn, {'id': agent, 'seen': False, 'stopped': False})
        elif event == 'SubagentStop' and agent:
            if turn in workers and workers[turn]['id'] == agent:
                workers[turn]['stopped'] = True
        elif event == 'PreToolUse' and not agent and turn == state['turn']:
            state['launches'] += 1
            args = payload.get('tool_input', {})
            if (args.get('model'), args.get('reasoning_effort')) == ASTRA_TRIAL:
                state['measured_launch'] = args.get('task_name')
        elif event == 'PostModelRequest':
            if agent:
                if turn not in workers or workers[turn]['id'] != agent:
                    if state.get('previous_workers', {}).get(turn) != agent:
                        state['partial'] = True
                    return {}
                workers[turn]['seen'] = True
            state['models'][model] = None
            if agent:
                phase = 'worker'
                state.setdefault('worker_models', {})[model] = None
            else:
                state.setdefault('coordinators', {})[model] = None
                phase = 'verification' if workers and all(w['stopped'] for w in workers.values()) else 'setup'
            counts = payload.get('token_usage')
            total = counts.get('total_tokens') if isinstance(counts, dict) else None
            if type(total) is int and total >= 0:
                state['total'] += total
                state['seen'] += 1
                add_counts(state.setdefault('phases', {}), phase, counts)
            else:
                state['partial'] = True
        elif event == 'Stop' and turn == state['turn'] and payload.get('last_assistant_message'):
            state['reported'] = True
            models = ' + '.join(state['models']) or model
            if not state['seen']:
                return {'systemMessage': f'Switch Power · {models} · token usage unavailable'}
            incomplete = (state['partial'] or state['launches'] > len(workers) or
                          any(not w['seen'] or not w['stopped'] for w in workers.values()))
            try:
                save_route(state, store, incomplete)
            except (OSError, ValueError):
                # An unavailable history does not invalidate this turn's usage notice.
                pass
            suffix = ' (partial)' if incomplete else ''
            return {'systemMessage': f"Switch Power · {models} · {state['total']:,} tokens{suffix}"}
    return {}
