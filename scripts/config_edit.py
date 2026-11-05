"""Conservative edits to selected scalar TOML keys, preserving unrelated text."""
import json
import copy
import os
from pathlib import Path
import re
import tempfile
import tomllib


def statement_lines(lines):
    """Return line starts outside TOML strings and multiline value containers."""
    active = set()
    mode, depth = None, 0
    for number, line in enumerate(lines):
        if mode is None and depth == 0:
            active.add(number)
        i = 0
        while i < len(line):
            char = line[i]
            if mode in {'"""', "'''"}:
                if mode == '"""' and char == '\\':
                    i += 2
                    continue
                if line.startswith(mode, i):
                    quote = mode[0]
                    while i < len(line) and line[i] == quote:
                        i += 1
                    mode = None
                    continue
            elif mode in {'"', "'"}:
                if mode == '"' and char == '\\':
                    i += 2
                    continue
                if char == mode:
                    mode = None
            else:
                if char == '#':
                    break
                if char in {'"', "'"}:
                    mode = char * 3 if line.startswith(char * 3, i) else char
                    i += len(mode)
                    continue
                if char in '[{':
                    depth += 1
                elif char in ']}':
                    depth -= 1
            i += 1
    return active


def table_path(header):
    try:
        value = tomllib.loads(header + '\n__switch_power_probe__ = true\n')
        path = []
        while isinstance(value, dict) and '__switch_power_probe__' not in value:
            if len(value) != 1:
                return None
            key, value = next(iter(value.items()))
            path.append(key)
        return tuple(path) if isinstance(value, dict) else None
    except tomllib.TOMLDecodeError:
        return None


def set_value(text, table, key, value, remove=False):
    original = tomllib.loads(text)
    lines = text.splitlines(keepends=True)
    active = statement_lines(lines)
    current = ()
    start, end = (0, len(lines)) if not table else (None, None)
    for i, line in enumerate(lines):
        if i not in active:
            continue
        stripped = line.strip()
        if stripped.startswith('['):
            next_table = table_path(stripped)
            if current == table and start is not None and end == len(lines):
                end = i
            current = next_table
            if current == table:
                start, end = i + 1, len(lines)
    if start is None:
        if remove:
            return text
        header = '[' + '.'.join(json.dumps(v) for v in table) + ']\n'
        result = text + ('\n' if text and not text.endswith('\n\n') else '') + header
        result += key + ' = ' + json.dumps(value, ensure_ascii=False) + '\n'
    else:
        key_pattern = '(?:' + '|'.join(re.escape(k) for k in [key, '"' + key + '"', "'" + key + "'"]) + ')'
        found = [i for i in range(start, end) if i in active and
                 re.match(r'^\s*' + key_pattern + r'\s*=', lines[i])]
        encoded = str(value).lower() if isinstance(value, bool) else json.dumps(value, ensure_ascii=False)
        replacement = key + ' = ' + encoded + '\n'
        if found:
            lines[found[0]] = '' if remove else replacement
        elif not remove:
            if end > 0 and not lines[end - 1].endswith('\n'):
                lines[end - 1] += '\n'
            lines.insert(end, replacement)
        result = ''.join(lines)
    expected = copy.deepcopy(original)
    target = expected
    for segment in table:
        target = target.setdefault(segment, {})
    if remove:
        target.pop(key, None)
    else:
        target[key] = value
    if tomllib.loads(result) != expected:
        raise ValueError('Unsupported TOML layout; refusing to alter unrelated settings')
    return result


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Refusing to replace a symlink: ' + str(path))
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.switch-power-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
