"""Recompute a run's summary from its append-only ledger without model calls."""
import argparse
import json
from .run import summarize
from .watch import resolve


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',nargs='?',default='latest')
    args=parser.parse_args()
    print(json.dumps(summarize(resolve(args.run)),indent=2))

if __name__=='__main__':main()
