"""Muvi's CLI. Help, version and MCP configuration have no DSP imports."""

import argparse
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

from genome import __version__


class UsageError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def timestamp(value):
    """Seconds, MM:SS or HH:MM:SS; no signed or overflowing clock fields."""
    try:
        if not re.fullmatch(r"\d+(?:\.\d+)?|\d+:\d{1,2}(?:\.\d+)?|\d+:\d{1,2}:\d{1,2}(?:\.\d+)?", value):
            raise ValueError
        parts = [float(part) for part in value.split(":")]
        if any(part >= 60 for part in parts[1:]):
            raise ValueError
        seconds = sum(part * 60 ** i for i, part in enumerate(reversed(parts)))
        if not math.isfinite(seconds):
            raise ValueError
        return seconds
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use non-negative seconds, MM:SS or HH:MM:SS") from exc


def common(parser, child=False):
    default = argparse.SUPPRESS if child else None
    parser.add_argument("--data-dir", type=Path, default=default, metavar="DIR", help="Library (default: MUVI_DATA_DIR or ~/.muvi)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", dest="format", action="store_const", const="json", default=default,
                       help="One JSON document on stdout; diagnostics stay on stderr")
    group.add_argument("--format", choices=["text", "json"], default=default, help="Explicit output format")
    parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS if child else False,
                        help="Suppress progress on stderr")


def build_parser():
    parser = Parser(prog="muvi", description="Music, made legible. Local evidence for your terminal and LLMs.",
                    epilog="Start: muvi demo  |  muvi analyze song.wav  |  muvi inspect latest --json\n"
                           "TRACK accepts an audio path, full ID, unique prefix (8+ characters), or latest.",
                    formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"muvi {__version__}")
    common(parser)
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def command(name, help, track=False, **kwargs):
        p = sub.add_parser(name, help=help, description=help, **kwargs)
        common(p, True)
        if track:
            p.add_argument("track", metavar="TRACK", help="Audio path, track ID/prefix, or latest")
        return p

    def interval(p, required=False):
        p.add_argument("--start", type=timestamp, required=required, default=0, metavar="TIME")
        p.add_argument("--end", type=timestamp, required=required, metavar="TIME")

    def output(p, default=None):
        p.add_argument("-o", "--output", type=Path, default=default, metavar="FILE")
        p.add_argument("--force", action="store_true", help="Replace an existing export (never source/cache files)")

    p = command("analyze", "Analyze local audio and print its musical evidence")
    p.add_argument("path", type=Path, metavar="AUDIO")
    p.add_argument("--profile", choices=["fast"], default="fast")
    p = command("inspect", "Read a compact track digest and acoustic progression", track=True, aliases=["overview"])
    p.add_argument('--flow-offset', type=int, default=0, help='Continue a paged acoustic progression')
    p = command("window", "Summarize exact-span energy, texture, activity and rhythm", track=True)
    interval(p)
    command("list", "List analyzed tracks, newest first")
    command("demo", "Analyze a deterministic generated example; no download needed")
    p = command("rhythm", "Inspect band attacks, local pulse rate and gaps; meter stays unresolved", track=True)
    interval(p)
    p.add_argument("--band", choices=["low", "mid", "high", "all"], default="low")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=128)
    p = command("beats", "Inspect tracked beat hypotheses, local tempo and onset support", track=True)
    interval(p)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=128)
    p = command("sections", "List all candidate sections or inspect one", track=True)
    p.add_argument("section", nargs="?", metavar="SECTION")
    p.add_argument("--detail", action="store_true", help="Include bounded event occurrences for a section")
    p = command("sounds", "Find acoustic objects by role or timbre", track=True)
    p.add_argument("--query", default="", help="For example: bass, beat, bright, sustained")
    interval(p)
    p = command("sound", "Inspect one acoustic object and paged occurrences", track=True)
    p.add_argument("sound", metavar="SOUND")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=100)
    p = command("evidence", "Retrieve measurements, units and provenance", track=True)
    p.add_argument("ids", nargs="+", metavar="EVIDENCE")
    p = command("compare", "Compare two sections or exact time ranges; changes are B minus A", track=True)
    p.add_argument("section_a", nargs='?', metavar="SECTION_A")
    p.add_argument("section_b", nargs='?', metavar="SECTION_B")
    p.add_argument('--a', nargs=2, type=timestamp, metavar=('START','END'), help='Exact first range')
    p.add_argument('--b', nargs=2, type=timestamp, metavar=('START','END'), help='Exact second range')
    p = command("verify", "Check a bounded musical hypothesis", track=True)
    p.add_argument("hypothesis", choices=["independent-bass", "instrument-identity", "recurring-pattern", "section-change"])
    p.add_argument("--sound", help="Limit the check to an acoustic object")
    p = command("metrics", "Read source-rate peak, RMS and stereo measurements", track=True)
    interval(p)
    p = command("crop", "Write an original-mixture WAV crop (maximum 60 seconds)", track=True)
    interval(p, True)
    output(p)
    p = command("render", "Write an aligned PNG and companion JSON legend", track=True)
    interval(p)
    output(p)
    p = command("export", "Export the complete canonical genome (stdout if no --output)", track=True)
    output(p)
    p = command("tools", "Discover the typed tool contract")
    p.add_argument("name", nargs="?", help="Tool to inspect, including its JSON input schema")
    p = command("tool", "Call a typed tool with JSON arguments")
    p.add_argument("name")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--arguments", default="{}", metavar="JSON")
    group.add_argument("--arguments-file", type=Path, metavar="FILE", help="UTF-8 JSON file, or - for stdin")
    command("schema", "Print the canonical genome JSON Schema")
    command("prompt", "Print grounding instructions for an LLM")
    command("mcp-config", "Print a stdio MCP client configuration for this installation")
    command("mcp", "Run the optional MCP stdio server")
    p = command("benchmark", "Evaluate deterministic controlled fixtures")
    output(p, Path("artifacts/benchmark.json"))
    return parser


def progress(args):
    def report(stage, fraction):
        if not args.quiet:
            print(f"  {round(fraction * 100):3}%  {stage}", file=sys.stderr, flush=True)
    return report


def resolve_track(reference, engine, args):
    path = Path(reference).expanduser()
    if path.is_file():
        return engine.analyze(path, progress=progress(args)).track_id
    tracks = engine.list_tracks()
    if reference == "latest":
        if not tracks:
            raise UsageError("Your library is empty. Run muvi analyze <audio> or muvi demo.")
        return tracks[0]['track_id']
    prefix = reference.removeprefix("sha256:")
    if re.fullmatch(r"[a-f0-9]{8,64}", prefix):
        matches = [t['track_id'] for t in tracks if t['track_id'].removeprefix("sha256:").startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise UsageError("Ambiguous track prefix. Use more characters or a full ID from muvi list --json.")
        raise UsageError("Track is not in this library. Check --data-dir or run muvi analyze <audio>.")
    raise UsageError(f"No audio file or track matches {reference!r}. Use a path, ID prefix (8+ characters), or latest.")


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)


def run(args):
    # Protocol/configuration commands have no incidental stdout or heavy imports.
    if args.command == "mcp-config":
        root = Path(args.data_dir or os.environ.get("MUVI_DATA_DIR", Path.home()/".muvi")).expanduser().resolve()
        return {"mcpServers": {"muvi": {"command": sys.executable,
                "args": ["-m", "genome.cli", "mcp", "--data-dir", str(root)]}}}
    if args.command == "mcp":
        try:
            from genome.mcp_server import create_mcp
        except ModuleNotFoundError as exc:
            if exc.name != "mcp":
                raise
            raise UsageError('MCP is optional. Install with: pip install "muvi-genome[mcp]" (checkout: uv sync --extra mcp)') from exc
        create_mcp(args.data_dir).run(transport="stdio")
        return None
    if args.command == "schema":
        from genome.schema import Genome
        return Genome.model_json_schema()
    from genome.engine import Engine
    from genome.tools import SYSTEM_PROMPT, MusicTools
    if args.command == "prompt":
        return {"system_prompt": SYSTEM_PROMPT} if args.format == "json" else SYSTEM_PROMPT
    engine = Engine(args.data_dir)
    tools = MusicTools(engine)
    track = resolve_track(args.track, engine, args) if hasattr(args, "track") else None
    if args.command in ("analyze", "demo"):
        if args.command == "demo":
            from genome.fixtures import synthesize
            with tempfile.TemporaryDirectory(prefix="muvi-demo-") as temp:
                path = Path(temp)/"Muvi demo.wav"
                synthesize(path)
                g = engine.analyze(path, progress=progress(args))
        else:
            g = engine.analyze(args.path.expanduser(), progress=progress(args))
        return tools.get_track_digest(g.track_id)
    if args.command in ("inspect", "overview"):
        return tools.get_track_digest(track, flow_offset=args.flow_offset)
    if args.command == "window":
        return tools.get_window(track, args.start, args.end)
    if args.command == "list":
        return {"tracks": engine.list_tracks()}
    if args.command == "rhythm":
        return tools.get_rhythm(track, args.start, args.end, args.band, args.offset, args.limit)
    if args.command == "beats":
        return tools.get_beats(track, args.start, args.end, args.offset, args.limit)
    if args.command == "sections":
        if args.detail and not args.section:
            raise UsageError("Use --detail with a SECTION ID from muvi sections TRACK.")
        if args.section:
            return tools.get_section(track, args.section, "detail" if args.detail else "summary")
        g = engine.load(track)
        return tools._packet(g, {"sections": [s.model_dump() for s in g.sections]},
                             [e for s in g.sections for e in s.evidence_ids])
    if args.command == "sounds":
        return tools.find_sound(track, args.query, args.start, args.end)
    if args.command == "sound":
        return tools.get_sound(track, args.sound, args.offset, args.limit)
    if args.command == "evidence":
        return tools.get_evidence(track, args.ids)
    if args.command == "compare":
        return tools.compare_sections(track, args.section_a, args.section_b, args.a, args.b)
    if args.command == "verify":
        return tools.verify_hypothesis(track, args.hypothesis.replace("-", "_"), args.sound)
    if args.command == "metrics":
        return tools.get_master_metrics(track, args.start, args.end)
    if args.command in ("crop", "render", "export"):
        from genome.exports import destination, write
        output = None
        if args.output:
            output = destination(args.output, engine, args.force, [args.track])
            suffix = {"crop": ".wav", "render": ".png", "export": ".json"}[args.command]
            if output.suffix.lower() != suffix:
                raise UsageError(f"Use a {suffix} output file for {args.command}.")
            if args.command == "render":
                legend_output = destination(output.with_suffix(".json"), engine, args.force, [args.track])
        if args.command == "export":
            g = engine.load(track)
            if not output:
                return g.model_dump()
            artifact = write(output, (g.model_dump_json(indent=2) + "\n").encode("utf-8"), args.force)
            return {"track_id": track, "analysis_id": g.analysis_id, **artifact}
        result = tools.get_audio_crop(track, args.start, args.end) if args.command == "crop" else tools.render_tile(track, args.start, args.end)
        if output:
            key = "audio" if args.command == "crop" else "image"
            result[key] = write(output, Path(result[key]['path']).read_bytes(), args.force)
            if args.command == "render":
                legend = json.loads(Path(result['legend']['path']).read_text(encoding="utf-8"))
                legend['raw_arrays'] = (engine.directory(track, result['analysis_id'])/"arrays/features.npz").as_uri()
                result['legend'] = write(legend_output, (encode(legend) + "\n").encode("utf-8"), args.force)
        return result
    if args.command == "tools":
        registry = tools.registry()
        if args.name:
            if args.name not in registry:
                raise UsageError("Unknown tool. Run muvi tools to see available tools.")
            return {"name": args.name, "description": registry[args.name].__doc__,
                    "input_schema": tools.schemas()[args.name].model_json_schema()}
        return {"tools": [{"name": name, "description": fn.__doc__} for name, fn in registry.items()]}
    if args.command == "tool":
        raw = args.arguments
        if args.arguments_file:
            raw = sys.stdin.read() if str(args.arguments_file) == "-" else args.arguments_file.read_text(encoding="utf-8-sig")
        arguments = json.loads(raw)
        if not isinstance(arguments, dict):
            raise UsageError("Tool arguments must be a JSON object.")
        if 'track_id' in arguments and isinstance(arguments['track_id'], str):
            arguments['track_id'] = resolve_track(arguments['track_id'], engine, args)
        return tools.call(args.name, arguments)
    if args.command == "benchmark":
        from genome.evaluate import benchmark
        from genome.exports import destination, write
        output = destination(args.output, engine, args.force)
        with tempfile.TemporaryDirectory(prefix="muvi-benchmark-report-") as temp:
            report = benchmark(Path(temp)/"report.json")
        write(output, (encode(report) + "\n").encode("utf-8"), args.force)
        return report
    raise UsageError("Unknown command")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    # Windows redirected streams default to a legacy code page; the CLI contract is UTF-8.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    wants_json = "--json" in argv or "--format=json" in argv or any(
        a == "--format" and b == "json" for a, b in zip(argv, argv[1:]))
    try:
        parser = build_parser()
        if not argv:
            parser.print_help()
            return
        args = parser.parse_args(argv)
        wants_json = args.format == "json"
        result = run(args)
        if result is None:
            return
        json_output = wants_json or args.command in ("schema", "mcp-config") or (args.command == "export" and not args.output)
        if json_output:
            print(encode(result))
        elif isinstance(result, str):
            print(result.rstrip())
        else:
            from genome.terminal import format_result
            print(format_result(args.command, result))
        if args.command == "benchmark" and not result['passed']:
            raise SystemExit(1)
    except BrokenPipeError:
        # Avoid a second broken pipe while Python flushes stdout during shutdown.
        with open(os.devnull, "w") as null:
            os.dup2(null.fileno(), sys.stdout.fileno())
    except KeyboardInterrupt:
        print("Muvi: interrupted.", file=sys.stderr)
        raise SystemExit(130) from None
    except (ValueError, KeyError, OSError, TimeoutError) as exc:
        from genome.terminal import clean
        message = str(exc.args[0]) if isinstance(exc, KeyError) else str(exc)
        if wants_json:
            print(encode({"error": {"code": "invalid_request", "message": message}}))
        print(f"Muvi: {clean(message)}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
