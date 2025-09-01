import asyncio
import argparse
import sys
from app.settings import settings

def main():
    parser = argparse.ArgumentParser(description="Multiagent Trader")
    parser.add_argument("--mode", choices=["BACKTEST", "PAPER", "LIVE"], default=None)
    args = parser.parse_args()
    if args.mode:
        settings.mode = args.mode

    if settings.mode.upper() in {"PAPER", "LIVE"} and settings.broker_provider != "paper":
        if not settings.oanda.api_key or not settings.oanda.account_id:
            print("Missing OANDA credentials for PAPER/LIVE mode with OANDA broker. Set OANDA_API_KEY and OANDA_ACCOUNT_ID.", flush=True)
            sys.exit(1)

    try:
        # Defer import to catch initialization errors
        from app.scheduler import run_scheduler
        print(f"Starting scheduler in {settings.mode} mode...")
        asyncio.run(run_scheduler())
    except ConnectionError as e:
        print(f"\n[ERROR] Could not start the application: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
