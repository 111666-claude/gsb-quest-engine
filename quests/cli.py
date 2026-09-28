"""命令行入口：跑任务链样例。"""

import argparse

from .engine import run, sample


def build_parser():
    parser = argparse.ArgumentParser(prog="quest-engine", description="任务链求值")
    parser.add_argument("--quests", default="sample", help="sample")
    return parser


def main(argv=None):
    build_parser().parse_args(argv)
    quests, events = sample()
    report = run(quests, events)
    print("completed=%s" % ",".join(report["completed"]))
    print("completed_count=%d rewards=%d cycles=%d"
          % (len(report["completed"]), report["rewards"], len(report["cycles"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
