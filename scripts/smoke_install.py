"""Run with an isolated core-only wheel installation, outside the checkout."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import genome
from genome.fixtures import synthesize

repository = Path(__file__).resolve().parents[1]
module_path = Path(genome.__file__).resolve()
assert not module_path.is_relative_to(repository), 'Test the installed wheel, not the checkout'
assert not (module_path.parent/'server.py').exists()
assert not list((module_path.parent/'static').glob('*'))
for package in ('fastapi', 'uvicorn', 'starlette', 'mcp'):
    assert importlib.util.find_spec(package) is None, f'{package} must not be a core dependency'

with tempfile.TemporaryDirectory(prefix='muvi-wheel-smoke-') as temp:
    root = Path(temp)
    source = root/'음악 with spaces.wav'
    synthesize(source, duration=4, kind='pulse')

    def cli(*args, code=0):
        result = subprocess.run([sys.executable, '-m', 'genome.cli', '--data-dir', str(root/'store'),
                                 *map(str, args), '--json'], capture_output=True, text=True,
                                encoding='utf-8', timeout=60, cwd=root)
        assert result.returncode == code, result.stderr
        assert 'Traceback' not in result.stderr
        return json.loads(result.stdout)

    digest = cli('analyze', source)
    assert digest['title'] == source.stem
    assert cli('inspect', 'latest') == digest
    assert cli('tools', 'get_audio_crop')['input_schema']
    assert cli('crop', 'latest', '--start', '0.2', '--end', '0.3', '-o', root/'crop.wav')['audio']['path']
    assert cli('render', 'latest', '--end', '2', '-o', root/'tile.png')['image']['path']
    assert cli('export', 'latest')['track_id'] == digest['track_id']
    assert cli('mcp-config')['mcpServers']['muvi']['command'] == sys.executable
    assert 'optional' in cli('mcp', code=2)['error']['message']

print(json.dumps({'version': genome.__version__, 'installed_module': str(module_path),
                  'result': 'passed: core-only CLI analysis, evidence, crop, chart, export, MCP configuration and missing-extra error'}))
