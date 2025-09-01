import asyncio
import argparse
from app.settings import settings
from app.scheduler import run_scheduler


def main():
    parser = argparse.ArgumentParser(description="Multiagent Trader")
    parser.add_argument("--mode", choices=["BACKTEST","PAPER","LIVE"], default=None)
    args = parser.parse_args()
    if args.mode:
        settings.mode = args.mode
    asyncio.run(run_scheduler())

if __name__ == "__main__":
    main()
