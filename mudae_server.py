"""MudaDemote Headless 24/7 Server Runner with Web Dashboard.

Usage:
    python mudae_server.py [--host 0.0.0.0] [--port 8080] [--preset MyPreset] [--autostart]
"""

import argparse
import asyncio
import gc
import os
import signal
import sys
from aiohttp import web

# Configure UTF-8 console output for cross-platform support (Windows/Linux/EC2)
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Maximum performance async event loop optimization for Linux / AWS EC2
if sys.platform != "win32":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

from mudae_core.config import load_json, atomic_write_json
from mudae_core.bot_runtime import RuntimeManager, InstanceEvent
from mudae_web.app import WebServerContext, create_app


async def periodic_memory_optimization():
    """Periodically perform garbage collection and memory trim for low-RAM EC2 instances."""
    gc.set_threshold(50000, 10, 10)
    while True:
        try:
            await asyncio.sleep(600)  # Run every 10 minutes
            gc.collect(1)
        except asyncio.CancelledError:
            break
        except Exception:
            pass


def get_base_dir() -> str:
    """Return project root directory."""
    return os.path.dirname(os.path.abspath(__file__))


def parse_args():
    parser = argparse.ArgumentParser(description="MudaDemote 24/7 Headless Server Edition")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Web dashboard host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")), help="Web dashboard port (default: 8080)")
    parser.add_argument("--preset", default=os.getenv("PRESET", "Example"), help="Default preset to run")
    parser.add_argument("--autostart", action="store_true", default=os.getenv("AUTOSTART", "false").lower() in ("true", "1"), help="Automatically start bot on launch")
    return parser.parse_args()


async def main():
    args = parse_args()
    base_dir = get_base_dir()
    presets_path = os.path.join(base_dir, "presets.json")

    # Ensure presets.json exists
    if not os.path.exists(presets_path):
        example_path = os.path.join(base_dir, "presets.example.json")
        default_data = load_json(example_path, {"Example": {}})
        atomic_write_json(presets_path, default_data)

    print(f"=========================================================")
    print(f">> MudaDemote | Server Edition (Headless & Web Dashboard)")
    print(f"=========================================================")
    print(f"Base Directory: {base_dir}")
    print(f"Presets File:   {presets_path}")
    print(f"Web Dashboard:  http://{args.host}:{args.port}")
    print(f"Active Preset:  {args.preset}")
    print(f"=========================================================")

    # Initialize Context & Runtime Manager
    context = WebServerContext(presets_path=presets_path, default_preset=args.preset)

    def on_runtime_event(event: InstanceEvent):
        # Broadcast runtime events to WebSocket clients
        event_dict = event.to_dict()
        context.broadcast_event(event.event_type, event_dict.get("data", {}))

    runtime_mgr = RuntimeManager(event_callback=on_runtime_event)
    context.runtime_manager = runtime_mgr

    # Build web app
    app = create_app(context)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, args.host, args.port)
    await site.start()
    print(f"Web Dashboard started and listening on http://{args.host}:{args.port}")

    # Launch background memory optimization for 24/7 low-footprint EC2 runtime
    mem_task = asyncio.create_task(periodic_memory_optimization())

    # Autostart bot if requested and credentials are available
    if args.autostart:
        presets = load_json(presets_path, {})
        target_preset = presets.get(args.preset)
        if target_preset and target_preset.get("token"):
            print(f"Autostarting bot instance for preset '{args.preset}'...")
            try:
                instance_id = runtime_mgr.start_instance(
                    args.preset, target_preset, {"token": target_preset["token"]}, block=False
                )
                context.active_instance_id = instance_id
                print(f"Instance started with ID: {instance_id}")
            except Exception as e:
                print(f"Failed to autostart instance: {e}")

    # Graceful stop handler
    stop_event = asyncio.Event()

    def signal_handler():
        print("\nShutdown signal received. Stopping server...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except (NotImplementedError, AttributeError):
            pass

    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        print("Cleaning up runtime manager instances...")
        mem_task.cancel()
        runtime_mgr.shutdown_all(timeout=5.0)
        await runner.cleanup()
        print("Server stopped cleanly.")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
