#!/usr/bin/env python3
"""Prepare a personal venv explicitly; otherwise only check the selected environment."""
import argparse
import datetime
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile

REFERENCE_PYTHON = '3.12.14'
MODULES = ('fastmcp', 'pydantic', 'pytest', 'matplotlib')
TOOLS = ('bash', 'git', 'ssh', 'ssh-keygen', 'curl', 'nano', 'ls', 'mkdir',
         'touch', 'cp', 'mv', 'rm', 'cat', 'head', 'tail', 'wc', 'grep',
         'chmod', 'clear', 'file', 'diff', 'mktemp')
MANUAL = [
    'Вход учебной учётной записью; сохранность файлов и окружения после выхода.',
    'GitLab: clone/commit/push и доступ к настоящим файлам, Git LFS при его использовании.',
    'Браузер: платформа, авторизация, локальные HTML/PNG, разрешённые сервисы ИИ.',
    'Сеть в голодные дни/экзамены; VPN/прокси только в разрешённом режиме.',
    'LibreOffice Calc: CSV и кириллица; презентация и экспорт PDF; запись экрана со звуком.',
    'Проверка каждого используемого образа ОС/архитектуры; этот отчёт относится к одному ПК.',
]


def clean_env():
    # Preserve campus network settings, but not variables redirecting installation.
    pip_network = {'PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL', 'PIP_CERT',
                   'PIP_CLIENT_CERT', 'PIP_TRUSTED_HOST', 'PIP_PROXY',
                   'PIP_TIMEOUT', 'PIP_RETRIES', 'PIP_CONFIG_FILE'}
    env = {k: v for k, v in os.environ.items()
           if (not k.startswith('PIP_') or k in pip_network)
           and k not in ('PYTHONHOME', 'PYTHONPATH')}
    env['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    return env


def run(argv, cwd=None, timeout=60):
    process = subprocess.Popen([str(a) for a in argv], cwd=cwd, env=clean_env(),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=(os.name != 'nt'))
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        raise RuntimeError('Превышено время команды: ' + str(argv) + '\n' + stdout + stderr)
    if process.returncode:
        raise RuntimeError('Код ' + str(process.returncode) + ': ' + str(argv)
                           + '\n' + stdout + stderr)
    return {'stdout': stdout.strip(), 'stderr': stderr.strip()}


def check(results, name, fn):
    print('Проверка: ' + name, file=sys.stderr, flush=True)
    try:
        results.append({'id': name, 'status': 'PASS', 'evidence': fn()})
    except Exception as exc:
        results.append({'id': name, 'status': 'FAIL',
                        'evidence': type(exc).__name__ + ': ' + str(exc)})


def pins(path):
    result = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([\w.-]+)==([\w.!+-]+)(?:\s*;\s*(.+))?', line)
        if not match:
            raise ValueError('В lock-файле нужны точные name==version, строка ' + str(number))
        name, version, marker = match.groups()
        result.append((re.sub(r'[-_.]+', '-', name).lower(), version, marker))
    missing = set(MODULES) - {name for name, _, marker in result if not marker}
    if missing:
        raise ValueError('В lock-файле отсутствуют обязательные пакеты: ' + ', '.join(sorted(missing)))
    return result


def validate_output(output, requirements, target, project_dir, wheelhouse):
    if output.is_symlink():
        raise ValueError('--output не должен быть символической ссылкой: ' + str(output))
    if output.exists():
        if output.is_dir():
            raise ValueError('--output должен указывать на файл, а не каталог: ' + str(output))
        if output.stat().st_nlink > 1:
            raise ValueError('--output не должен быть жёсткой ссылкой: ' + str(output))
    destination = output.resolve()
    for protected in (Path(__file__), requirements):
        if (destination == protected.resolve()
                or (output.exists() and protected.exists() and output.samefile(protected))):
            raise ValueError('--output совпадает с входным файлом: ' + str(protected))
    roots = [target, project_dir, wheelhouse]
    if sys.prefix != sys.base_prefix:
        roots.append(Path(sys.prefix))
    for root in roots:
        if root is not None and destination.is_relative_to(root.resolve()):
            raise ValueError('--output нельзя сохранять внутри venv, проекта или wheelhouse: '
                             + str(root))


def write_report(path, report):
    data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', suffix='.tmp',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def inspect_venv(target):
    cfg = target / 'pyvenv.cfg'
    if not cfg.is_file():
        raise ValueError('Это не venv (нет pyvenv.cfg): ' + str(target))
    settings = dict(line.lower().split('=', 1) for line in cfg.read_text().splitlines() if '=' in line)
    settings = {key.strip(): value.strip() for key, value in settings.items()}
    if settings.get('include-system-site-packages') != 'false':
        raise ValueError('Нужен изолированный venv без system-site-packages: ' + str(target))
    # Do not resolve this symlink: it must still select the venv, not the base Python.
    executable = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    info = json.loads(run([executable, '-I', '-c',
        'import json,sys; print(json.dumps({"prefix":sys.prefix,"base":sys.base_prefix,'
        '"version":list(sys.version_info[:3]),"executable":sys.executable}))'])['stdout'])
    if Path(info['prefix']).resolve() != target.resolve() or info['prefix'] == info['base']:
        raise ValueError('Python не принадлежит выбранному venv: ' + str(info))
    if tuple(info['version']) < (3, 12):
        raise ValueError('Нужен Python 3.12 или новее; найден ' + str(info['version']))
    return executable


def prepare(target, requirements, wheelhouse, results):
    if wheelhouse is not None and not wheelhouse.is_dir():
        raise ValueError('Папка wheelhouse не существует: ' + str(wheelhouse))
    if target.exists() and (not target.is_dir() or
                            (not (target / 'pyvenv.cfg').is_file() and any(target.iterdir()))):
        raise ValueError('Непустая папка не является venv; содержимое сохранено: ' + str(target))
    if not (target / 'pyvenv.cfg').is_file():
        if sys.version_info < (3, 12):
            raise ValueError('Запустите подготовку через установленный Python 3.12 или новее.')
        print('Создание venv: ' + str(target), file=sys.stderr, flush=True)
        run([sys.executable, '-m', 'venv', target], timeout=120)
    executable = inspect_venv(target)
    results.append({'id': 'prepare-venv', 'status': 'PASS', 'evidence': str(target)})
    argv = [executable, '-m', 'pip', '--require-virtualenv', '--disable-pip-version-check',
            'install', '--no-input', '--only-binary=:all:', '--no-deps', '-r', requirements]
    if wheelhouse is not None:
        argv += ['--no-index', '--find-links', wheelhouse]
    print('Установка пакетов' + (' из локального wheelhouse.' if wheelhouse else ' из настроенного источника пакетов.'),
          file=sys.stderr, flush=True)
    evidence = run(argv, timeout=600)
    results.append({'id': 'install-packages', 'status': 'PASS', 'evidence': evidence})


def locked_versions(required):
    from packaging.markers import Marker
    versions, errors = {}, []
    for name, expected, marker in required:
        if marker and not Marker(marker).evaluate():
            continue
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = 'MISSING'
        versions[name] = actual
        if actual != expected:
            errors.append(name + ': требуется ' + expected + ', найдено ' + actual)
    if errors:
        raise RuntimeError('\n'.join(errors))
    return versions


def dependency(name):
    importlib.import_module(name)
    return {'module': name, 'version': importlib.metadata.version(name)}


def database():
    with tempfile.TemporaryDirectory(prefix='bassein-sqlite-') as temp:
        path = Path(temp) / 'probe.db'
        with sqlite3.connect(path) as conn:
            conn.execute('CREATE TABLE probe (value TEXT)')
            conn.execute('INSERT INTO probe VALUES (?)', ('Проверка',))
        with sqlite3.connect(path) as conn:
            if conn.execute('SELECT value FROM probe').fetchone() != ('Проверка',):
                raise RuntimeError('Не удалось прочитать сохранённую строку.')
    return {'version': sqlite3.sqlite_version, 'write_read_utf8': True}


def plot():
    with tempfile.TemporaryDirectory(prefix='bassein-plot-') as temp:
        previous = os.environ.get('MPLCONFIGDIR')
        os.environ['MPLCONFIGDIR'] = temp
        try:
            import matplotlib
            matplotlib.use('Agg')
            from matplotlib import pyplot as plt
            path = Path(temp) / 'plot.png'
            plt.plot([1, 2], [1, 4])
            plt.savefig(path)
            plt.close()
            data = path.read_bytes()
            if len(data) < 100 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
                raise RuntimeError('PNG не создан или повреждён.')
            return {'backend': matplotlib.get_backend(), 'png_bytes': len(data)}
        finally:
            if previous is None:
                os.environ.pop('MPLCONFIGDIR', None)
            else:
                os.environ['MPLCONFIGDIR'] = previous


def shell_tools():
    found = {name: shutil.which(name) for name in TOOLS}
    missing = [name for name, path in found.items() if path is None]
    if missing:
        raise RuntimeError('Не найдены команды: ' + ', '.join(missing))
    return found


def shell_behaviour():
    # cross-platform shell behaviour
    probes = [
        ("printf 'a\nb\na\n' | grep -c a", '2'),
        ("printf 'a\nb\n' | tail -n +2", 'b'),
        ("printf 'a\nb\n' | wc -l", '2'),
        ("printf 'hello\n' | cat", 'hello'),
        ("printf 'a\tb\n' | python3 -c 'import sys; s=sys.stdin.read(); sys.stdout.write(s.replace(\"\\t\", \"^I\").replace(\"\\n\", \"$\"))'", 'a^Ib$')
    ]
    for command, expected in probes:
        actual = run(['bash', '-o', 'pipefail', '-c', command])['stdout'].strip()
        if actual != expected:
            raise RuntimeError(command + ': ожидается ' + expected + ', получено ' + actual)
    return 'grep -c; tail -n +2; wc -l; cat; tab/newline visibility (Python)'


def project_probe(source):
    for name in ('check_environment.py', 'client.py', 'testing/test_example.py'):
        if not (source / name).is_file():
            raise ValueError('Нужна папка стартового Д8Т2; отсутствует ' + name)
    with tempfile.TemporaryDirectory(prefix='bassein-mcp-') as temp:
        target = Path(temp) / 'project'
        def ignore(directory, names):
            excluded = set(shutil.ignore_patterns('.git', '.venv', 'venv', '__pycache__',
                '.pytest_cache', 'logs', '*.db', '*.db-*', '*.sqlite*')(directory, names))
            excluded.update(name for name in names if (Path(directory) / name).is_symlink()
                            or (Path(directory) / name / 'pyvenv.cfg').is_file())
            return excluded
        shutil.copytree(source, target, ignore=ignore)
        environment = run([sys.executable, 'check_environment.py'], cwd=target)
        demo = run([sys.executable, 'client.py', 'demo'], cwd=target, timeout=120)
        log = target / 'logs/client.jsonl'
        records = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        if any(row.get('event') == 'protocol_error'
               or row.get('result', {}).get('protocol_error') is True for row in records):
            raise RuntimeError('MCP-demo записал protocol_error: '
                               + json.dumps(records, ensure_ascii=False))
        calls = {row['arguments']['product_id']: row['result'] for row in records
                 if row.get('tool') == 'get_product'}
        hoodie, missing = calls.get('hoodie', {}), calls.get('missing', {})
        data = hoodie.get('data', {})
        if (hoodie.get('ok') is not True or data.get('id') != 'hoodie'
                or data.get('price_coins') != 500
                or data.get('stock') != {'S': 3, 'M': 5, 'L': 2, 'XL': 1}
                or missing.get('ok') is not False
                or missing.get('error', {}).get('code') != 'PRODUCT_NOT_FOUND'):
            raise RuntimeError('MCP-demo не вернул ожидаемые ответы: '
                               + json.dumps(records, ensure_ascii=False))
        tests = run([sys.executable, '-m', 'pytest', 'testing/test_example.py', '-q'],
                    cwd=target, timeout=120)
        if not re.search(r'\b1 passed\b', tests['stdout']):
            raise RuntimeError('Не подтверждён один стартовый тест: ' + str(tests))
    return {'environment': environment, 'demo': demo, 'mcp_responses': calls, 'pytest': tests,
            'source_unchanged': True, 'student_TODOs_not_tested': True}


def checks(args, required, report):
    results = report['checks']
    if sys.version_info < (3, 12):
        raise ValueError('Нужен Python 3.12 или новее.')
    check(results, 'venv', lambda: str(inspect_venv(Path(sys.prefix))))
    results.append({'id': 'python', 'status': 'PASS', 'evidence': platform.python_version()})
    if platform.python_version() != REFERENCE_PYTHON:
        results.append({'id': 'reference-python', 'status': 'WARN',
                        'evidence': 'Профиль материалов: ' + REFERENCE_PYTHON
                        + '; используется ' + platform.python_version()
                        + '. Это не подтверждение прогона на эталонной версии.'})
    check(results, 'locked-versions', lambda: locked_versions(required))
    check(results, 'pip-check', lambda: run([sys.executable, '-m', 'pip', 'check']))
    for name in MODULES:
        check(results, name, lambda name=name: dependency(name))
    check(results, 'sqlite', database)
    check(results, 'matplotlib-render', plot)
    check(results, 'shell-tools', shell_tools)
    for name, flag in (('git', '--version'), ('ssh', '-V'), ('bash', '--version'),
                       ('curl', '--version')):
        check(results, name, lambda name=name, flag=flag: run([name, flag]))
    check(results, 'shell-behaviour', shell_behaviour)
    if args.project_dir:
        check(results, 'project-d8', lambda: project_probe(args.project_dir))
    else:
        results.append({'id': 'project-d8', 'status': 'SKIP',
                        'evidence': 'Для проверки MCP и стартового теста укажите --project-dir Д8Т2.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Создать venv и установить пакеты.')
    parser.add_argument('--venv', type=Path, help='Путь личного venv; для --prepare по умолчанию .venv.')
    parser.add_argument('--requirements', type=Path,
                        default=Path(__file__).with_name('requirements-campus.lock.txt'))
    parser.add_argument('--wheelhouse', type=Path, help='Локальные wheels: установка без обращения к сети.')
    parser.add_argument('--project-dir', type=Path, help='Стартовый Д8Т2 для настоящего MCP-demo и теста.')
    parser.add_argument('--output', type=Path, required=True, help='JSON-отчёт.')
    args = parser.parse_args()
    for name in ('venv', 'requirements', 'wheelhouse', 'project_dir', 'output'):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.expanduser().absolute())
    target = args.venv or (Path.cwd() / '.venv' if args.prepare else None)
    try:
        validate_output(args.output, args.requirements, target, args.project_dir, args.wheelhouse)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    report = {'scope': 'current_machine_only', 'mode': 'prepare' if args.prepare else 'check',
              'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'python': platform.python_version(), 'executable': sys.executable,
              'os': platform.platform(), 'architecture': platform.machine(),
              'requirements': str(args.requirements), 'checks': [], 'manual_required': MANUAL}
    try:
        if os.name == 'nt':
            raise ValueError('На Windows запустите скрипт внутри WSL2 с Linux Python; команды заданий требуют Bash.')
        if args.wheelhouse is not None and not args.prepare:
            raise ValueError('--wheelhouse используется только вместе с --prepare.')
        required = pins(args.requirements)
        if args.prepare:
            prepare(target, args.requirements, args.wheelhouse, report['checks'])
        if target is not None:
            executable = inspect_venv(target)
            if Path(sys.prefix).resolve() != target.resolve():
                with tempfile.TemporaryDirectory(prefix='bassein-report-') as temp:
                    child_report = Path(temp) / 'report.json'
                    argv = [executable, Path(__file__).absolute(), '--venv', target,
                            '--requirements', args.requirements, '--output', child_report]
                    if args.project_dir:
                        argv += ['--project-dir', args.project_dir]
                    try:
                        run(argv, timeout=420)
                    except RuntimeError:
                        if not child_report.is_file():
                            raise
                    child = json.loads(child_report.read_text(encoding='utf-8'))
                child['checks'] = report['checks'] + child['checks']
                child['mode'] = report['mode']
                report = child
            else:
                checks(args, required, report)
        else:
            checks(args, required, report)
    except Exception as exc:
        report['checks'].append({'id': 'preparation' if args.prepare else 'environment',
                                 'status': 'FAIL', 'evidence': type(exc).__name__ + ': ' + str(exc)})
    failed = any(row['status'] == 'FAIL' for row in report['checks'])
    report['automatic_checks_passed'] = not failed
    report['project_checked'] = any(row['id'] == 'project-d8' and row['status'] == 'PASS'
                                    for row in report['checks'])
    try:
        write_report(args.output, report)
    except OSError as exc:
        print('Не удалось записать отчёт: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({'checks': {row['id']: row['status'] for row in report['checks']},
                      'report': str(args.output), 'scope': report['scope']}, ensure_ascii=False))
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())