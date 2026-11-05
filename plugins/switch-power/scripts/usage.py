"""Record observed native model attempts and render one post-answer notice."""
import re


def model_name(value):
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}', value):
        return value
    return 'unknown model'


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
            state.clear()
            state.update(turn=turn, workers={}, models={}, total=0, seen=0, launches=0,
                         partial=False, reported=False, previous_workers=previous_workers)
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
        elif event == 'PostModelRequest':
            if agent:
                if turn not in workers or workers[turn]['id'] != agent:
                    if state.get('previous_workers', {}).get(turn) != agent:
                        state['partial'] = True
                    return {}
                workers[turn]['seen'] = True
            state['models'][model] = None
            counts = payload.get('token_usage')
            total = counts.get('total_tokens') if isinstance(counts, dict) else None
            if type(total) is int and total >= 0:
                state['total'] += total
                state['seen'] += 1
            else:
                state['partial'] = True
        elif event == 'Stop' and turn == state['turn'] and payload.get('last_assistant_message'):
            state['reported'] = True
            models = ' + '.join(state['models']) or model
            if not state['seen']:
                return {'systemMessage': f'Switch Power · {models} · token usage unavailable'}
            incomplete = (state['partial'] or state['launches'] > len(workers) or
                          any(not w['seen'] or not w['stopped'] for w in workers.values()))
            suffix = ' (partial)' if incomplete else ''
            return {'systemMessage': f"Switch Power · {models} · {state['total']:,} tokens{suffix}"}
    return {}
