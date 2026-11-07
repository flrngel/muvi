import argparse
import json
import sys
from pathlib import Path

from genome import __version__
from genome.engine import Engine
from genome.tools import MusicTools


def main():
    parser = argparse.ArgumentParser(prog="muvi", description="Music, made legible. Local listening workspace and LLM evidence tools.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Open the local listening workspace")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--open", action="store_true", help="Open a browser")
    sub.add_parser("mcp", help="Run the MCP stdio tool server")
    analyze = sub.add_parser("analyze", help="Analyze a local audio file")
    analyze.add_argument("path", type=Path)
    analyze.add_argument("--profile", choices=["fast"], default="fast")
    digest = sub.add_parser("overview", help="Read a compact track digest")
    digest.add_argument("track_id")
    digest.add_argument("--format", choices=["json", "text"], default="json")
    render = sub.add_parser("render", help="Render an aligned image and JSON legend")
    render.add_argument("track_id")
    render.add_argument("--start", type=float, default=0)
    render.add_argument("--end", type=float)
    call = sub.add_parser("tool", help="Call any typed evidence tool")
    call.add_argument("name")
    call.add_argument("--arguments", default="{}", help="JSON tool arguments")
    sub.add_parser("list", help="List local analyzed tracks")
    benchmark = sub.add_parser("benchmark", help="Evaluate controlled generated fixtures")
    benchmark.add_argument("--output", type=Path, default=Path("artifacts/benchmark.json"))
    for child in sub.choices.values():
        child.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            import uvicorn
            from genome.server import create_app
            if args.open:
                import threading
                import webbrowser
                threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
            uvicorn.run(create_app(args.data_dir), host="127.0.0.1", port=args.port, log_level="warning")
            return
        if args.command == "mcp":
            from genome.mcp_server import create_mcp
            create_mcp(args.data_dir).run(transport="stdio")
            return
        tools = MusicTools(Engine(args.data_dir))
        if args.command == "analyze":
            result = tools.analyze_track(str(args.path), args.profile)
        elif args.command == "overview":
            result = tools.get_track_digest(args.track_id)
            if args.format == "text":
                print(result["digest_text"])
                return
        elif args.command == "render":
            result = tools.render_tile(args.track_id, args.start, args.end)
        elif args.command == "tool":
            result = tools.call(args.name, json.loads(args.arguments))
        elif args.command == "list":
            result = {"tracks": tools.engine.list_tracks()}
        else:
            from genome.evaluate import benchmark
            result = benchmark(args.output)
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
    except (ValueError, KeyError, OSError) as exc:
        print(f"Muvi: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()

