"""Public product tests through real terminal processes, including failure contracts."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from genome.cli import UsageError, resolve_track
from genome import __version__
from genome.engine import Engine
from genome.fixtures import synthesize
from genome.schema import Genome


def invoke(root, *arguments, code=0, stdin=None):
    result = subprocess.run([sys.executable, "-m", "genome.cli", "--data-dir", str(root), *map(str, arguments)],
                            input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert result.returncode == code, (result.args, result.stdout, result.stderr)
    assert "Traceback" not in result.stderr
    return result


def packet(root, *arguments, code=0, stdin=None):
    return json.loads(invoke(root, *arguments, "--json", code=code, stdin=stdin).stdout)


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    root = tmp_path_factory.mktemp("cli 음악 with spaces")
    source = root/"리듬 demo.wav"
    synthesize(source)
    result = invoke(root/"store", "analyze", source, "--json")
    digest = json.loads(result.stdout)
    assert "Saving" in result.stderr
    return root, source, digest


def test_analysis_cache_human_and_machine_output(library):
    root, source, digest = library
    cached = invoke(root/"store", "analyze", source, "--json")
    assert json.loads(cached.stdout) == digest
    assert "cached" in cached.stderr
    human = invoke(root/"store", "inspect", "latest").stdout
    assert "리듬 demo" in human
    assert "Candidate sections" in human and "unresolved" in human
    assert packet(root/"store", "overview", digest['track_id']) == digest
    prefix = digest['track_id'].removeprefix("sha256:")[:8]
    assert packet(root/"store", "inspect", prefix) == digest
    quiet = invoke(root/"store", "--json", "--quiet", "inspect", source)
    assert not quiet.stderr and json.loads(quiet.stdout) == digest
    assert packet(root/"store", "list")['tracks'][0]['track_id'] == digest['track_id']


def test_evidence_workflow(library):
    root, _, _ = library
    store = root/"store"
    sections = packet(store, "sections", "latest")['sections']
    first, last = sections[0]['id'], sections[-1]['id']
    assert "SECTION" in invoke(store, "sections", "latest").stdout
    assert "occurrences" in packet(store, "sections", "latest", first, "--detail")
    sounds = packet(store, "sounds", "latest", "--query", "bass", "--start", "00:00", "--end", "00:08")['matches']
    assert sounds
    sound = packet(store, "sound", "latest", sounds[0]['sound_object_id'], "--limit", "1")
    assert len(sound['occurrences']) == 1
    ev = packet(store, "evidence", "latest", *sounds[0]['evidence_ids'])
    assert ev['evidence'] and Path(ev['raw_arrays']['path']).exists()
    assert "url" not in ev['raw_arrays']
    comparison = packet(store, "compare", "latest", first, last)
    assert comparison['section_b']['id'] == last
    assert packet(store, "verify", "latest", "independent-bass")['verdict'] == "indeterminate"
    metrics = packet(store, "metrics", "latest", "--start", "00:01", "--end", "00:02")
    assert metrics['measurements']['integrated_lufs'] is None
    for arguments in [("sound", "latest", sounds[0]['sound_object_id'], "--limit", "1"),
                      ("evidence", "latest", "E0001"), ("compare", "latest", first, last),
                      ("verify", "latest", "section-change"), ("metrics", "latest")]:
        assert invoke(store, *arguments).stdout


def test_original_crops_chart_pair_and_genome_export(library):
    root, source, digest = library
    store = root/"store"
    audio = root/"exports"/"원본 clip.wav"
    crop = packet(store, "crop", "latest", "--start", "1.234", "--end", "00:02.135", "-o", audio)
    original, sr = sf.read(source, always_2d=True)
    clip, rate = sf.read(audio, always_2d=True)
    assert sr == rate
    np.testing.assert_array_equal(clip, original[crop['first_sample']:crop['end_sample_exclusive']])
    png = root/"exports"/"evidence.png"
    tile = packet(store, "render", "latest", "--start", "0", "--end", "3", "-o", png)
    assert Path(tile['image']['path']).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    legend = json.loads(png.with_suffix('.json').read_text(encoding='utf-8'))
    assert legend['time_span'] == tile['time_span']
    assert legend['raw_arrays'].startswith('file:')
    genome_path = root/"exports"/"genome.json"
    exported = packet(store, "export", "latest", "-o", genome_path)
    g = Genome.model_validate_json(genome_path.read_text(encoding='utf-8'))
    assert g.track_id == digest['track_id'] == exported['track_id']
    assert json.loads(invoke(store, "export", "latest").stdout) == g.model_dump()
    assert "Original mixture" in invoke(store, "crop", "latest", "--start", "0", "--end", "1").stdout
    assert "Image" in invoke(store, "render", "latest", "--end", "3").stdout


def test_exports_never_silently_overwrite_or_damage_source_cache(library):
    root, source, digest = library
    store = root/"store"
    output = root/"existing.json"
    output.write_text("keep me", encoding='utf-8')
    error = packet(store, "export", "latest", "-o", output, code=2)
    assert "--force" in error['error']['message']
    assert output.read_text() == "keep me"
    packet(store, "export", "latest", "-o", output, "--force")
    assert json.loads(output.read_text(encoding='utf-8'))['track_id'] == digest['track_id']
    original = source.read_bytes()
    packet(store, "crop", "latest", "--start", "0", "--end", "1", "-o", source, "--force", code=2)
    packet(store, "crop", source, "--start", "0", "--end", "1", "-o", source, "--force", code=2)
    assert source.read_bytes() == original
    cached = Engine(store).directory(digest['track_id'])/"genome.json"
    before = cached.read_bytes()
    packet(store, "export", "latest", "-o", cached, "--force", code=2)
    assert cached.read_bytes() == before
    png = root/"blocked.png"
    png.with_suffix('.json').write_text('keep legend')
    packet(store, "render", "latest", "-o", png, code=2)
    assert not png.exists() and png.with_suffix('.json').read_text() == 'keep legend'


def test_typed_tool_json_stdin_file_and_discovery(library):
    root, _, digest = library
    store = root/'store'
    arguments = json.dumps({'track_id': 'latest'})
    assert packet(store, 'tool', 'get_track_digest', '--arguments-file', '-', stdin=arguments) == digest
    path = root/'arguments.json'
    path.write_text(arguments, encoding='utf-8-sig')
    assert packet(store, 'tool', 'get_track_digest', '--arguments-file', path) == digest
    assert packet(store, 'tool', 'get_track_digest', '--arguments', arguments) == digest
    assert len(packet(store, 'tools')['tools']) == 14
    schema = packet(store, 'tools', 'get_audio_crop')['input_schema']
    assert {'track_id', 'start_s', 'end_s'} <= set(schema['required'])
    assert 'track_id' in packet(store, 'schema')['properties']
    assert 'indeterminate' in packet(store, 'prompt')['system_prompt']
    config = packet(store, 'mcp-config')['mcpServers']['muvi']
    assert config['command'] == sys.executable
    assert config['args'] == ['-m', 'genome.cli', 'mcp', '--data-dir', str(store.resolve())]


@pytest.mark.parametrize('arguments', [
    ['serve'], ['analyze', 'does not exist.wav'], ['inspect', 'missing'],
    ['crop', 'latest', '--start', '-1', '--end', '2'],
    ['crop', 'latest', '--start', '1:60', '--end', '2:00'],
    ['crop', 'latest', '--start', 'nan', '--end', '2'],
    ['crop', 'latest', '--start', '2', '--end', '1'],
    ['crop', 'latest', '--start', '0'], ['metrics', 'latest', '--end', '999'],
    ['tool', 'get_track_digest', '--arguments', '{'],
    ['tool', 'get_track_digest', '--arguments', '[]'],
    ['tool', 'get_track_digest', '--arguments', '{"track_id":"latest","bogus":true}'],
    ['tool', 'invented'], ['tools', 'invented'], ['evidence', 'latest', 'fake'],
    ['sound', 'latest', 'fake'], ['sections', 'latest', '--detail'],
])
def test_json_errors_have_exit_code_and_no_tracebacks(library, arguments):
    root, _, _ = library
    result = packet(root/'store', *arguments, code=2)
    assert result['error']['code'] == 'invalid_request'


def test_help_version_and_config_do_not_import_optional_or_dsp_packages(tmp_path):
    # -S disables site-packages. These commands must still work from the checkout.
    for arguments in [['--help'], ['--version'], ['mcp-config'], ['analyze', '--help']]:
        result = subprocess.run([sys.executable, '-S', '-m', 'genome.cli', *arguments],
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        assert result.returncode == 0, result.stderr
    assert __version__ in invoke(tmp_path/'store', '--version').stdout


def test_empty_library_environment_and_global_flags(tmp_path, monkeypatch):
    store = tmp_path/'library'
    assert 'empty' in invoke(store, 'list').stdout
    assert 'empty' in packet(store, 'inspect', 'latest', code=2)['error']['message']
    monkeypatch.setenv('MUVI_DATA_DIR', str(store))
    env = subprocess.run([sys.executable, '-m', 'genome.cli', '--json', 'list'],
                         capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert env.returncode == 0 and json.loads(env.stdout) == {'tracks': []}
    other = tmp_path/'other'
    assert packet(store, 'list', '--data-dir', other) == {'tracks': []}
    assert other.is_dir()


def test_ambiguous_prefix_fails():
    class Library:
        def list_tracks(self):
            return [{'track_id': 'sha256:abcdef00' + '0'*56}, {'track_id': 'sha256:abcdef00' + '1'*56}]
    with pytest.raises(UsageError, match='Ambiguous'):
        resolve_track('abcdef00', Library(), None)
    assert resolve_track('latest', Library(), None).endswith('0'*56)


def test_demo_is_repeatable_and_does_not_need_external_files(tmp_path):
    store = tmp_path/'store'
    first = packet(store, 'demo', '--quiet')
    second = packet(store, 'demo', '--quiet')
    assert first == second and first['title'] == 'Muvi demo'
    assert len(packet(store, 'list')['tracks']) == 1


def test_terminal_titles_cannot_inject_control_sequences(library):
    from genome.terminal import format_result
    _, _, digest = library
    result = format_result('inspect', {**digest, 'title': '\x1b[2Jmalicious\rtitle'})
    assert '\x1b' not in result and '\r' not in result


def test_cached_read_commands_do_not_load_dsp(library):
    root, source, _ = library
    script = '''
import sys
from genome.cli import main
for command in (['list'], ['inspect', 'latest'], ['analyze', sys.argv[2]],
                ['sounds', 'latest'], ['compare', 'latest', 'SEC_01', 'SEC_02'],
                ['metrics', 'latest'], ['rhythm', 'latest'], ['beats', 'latest'], ['tools']):
    main(['--data-dir', sys.argv[1], '--json', '--quiet', *command])
    assert not {'numpy', 'scipy', 'soundfile', 'matplotlib'} & set(sys.modules)
'''
    result = subprocess.run([sys.executable, '-c', script, str(root/'store'), str(source)],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stderr


def test_rhythm_cli_bounded_json_and_human_output(library):
    root, _, _ = library
    result = packet(root/'store', 'rhythm', 'latest', '--band', 'low', '--start', '0', '--end', '8', '--limit', '3')
    assert result['available'] and len(result['onset_times_s']) == 3
    assert result['next_offset'] == 3
    assert result['pulse']['pulse_rate_bpm'] is not None
    assert 'Acoustic pulse' in invoke(root/'store', 'rhythm', 'latest').stdout
    assert packet(root/'store', 'rhythm', 'latest', '--limit', '0', code=2)['error']
