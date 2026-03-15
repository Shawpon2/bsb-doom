import argparse
import signal
import sys
import time
import os
from .database.manager import DatabaseManager
from .core.engine import LoadTestEngine
from .core.attacks import AttackFactory
from .ui.console import LiveDisplay, print_banner, print_contact
from .utils.validators import validate_url
from .config import DEFAULT_CONCURRENCY, MAX_CONCURRENCY

def main():
    parser = argparse.ArgumentParser(description="BSB-DOOM Load Tester")
    parser.add_argument("target", help="Target URL or domain (e.g., example.com)")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"Concurrent connections (max {MAX_CONCURRENCY})")
    args = parser.parse_args()

    print_banner()

    # Validate target
    if not validate_url(args.target):
        print("[red]Invalid URL. Please include http:// or https://[/red]")
        sys.exit(1)

    # Database and block check
    db = DatabaseManager()
    machine_id = db.register_user()
    if db.is_blocked(machine_id):
        print("[red]You are blocked by the administrator.[/red]")
        print_contact()
        db.close()
        sys.exit(1)

    # Limit concurrency
    concurrency = min(args.concurrency, MAX_CONCURRENCY)

    # Use all attack methods
    attacks = AttackFactory.list_attacks()

    # Create engine
    engine = LoadTestEngine(args.target, concurrency, attacks)

    # Record session
    db.start_session(machine_id, args.target, os.getpid())

    # Start live display
    display = LiveDisplay(args.target)
    display.start()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n[yellow]Stopping test...[/yellow]")
        engine.stop()
        display.stop()
        db.end_session(machine_id)
        db.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    # Run engine in background
    engine.start()

    # Update display loop
    try:
        while not engine.stop_event.is_set():
            metrics = engine.get_metrics()
            display.update(metrics, engine.failure_load is not None)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        display.stop()

    # Final summary
    metrics = engine.get_metrics()
    total_time = time.time() - engine.start_time
    print("\n[bold cyan]--- Test Summary ---[/bold cyan]")
    print(f"Target: {args.target}")
    print(f"Duration: {total_time:.2f} seconds")
    print(f"Total Requests: {metrics.total_requests:,}")
    print(f"Peak RPS: {metrics.peak_rps:.1f}")
    print(f"Error Rate: {metrics.error_rate()*100:.1f}%")
    if engine.failure_load:
        print(f"[red]Site DOWN at {engine.failure_load:.1f} RPS[/red]")
    else:
        print("[green]Test stopped manually. Site survived the load.[/green]")

    # Save to database
    status = 'down' if engine.failure_load else 'success'
    db.add_test(machine_id, args.target, status,
                int(engine.failure_load) if engine.failure_load else int(metrics.peak_rps),
                int(total_time),
                metrics.peak_rps, metrics.error_rate(),
                metrics.avg_latency(), metrics.percentile(95))
    db.end_session(machine_id)
    db.close()

if __name__ == "__main__":
    main()
