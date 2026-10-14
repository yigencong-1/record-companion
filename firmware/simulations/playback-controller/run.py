"""Run with Python 3.10+; all execution and evidence remain local."""

import argparse
import hashlib
import json
import platform
import sys
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from controller import BASELINE, VERSION
from scenarios import CASES as BATCH1_CASES, Rig
from batch2_scenarios import CASES as BATCH2_CASES, DEFERRED, BatchRig


def json_default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, bytes):
        return {"hex": value.hex(), "length": len(value)}
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Unsupported evidence value: {type(value).__name__}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence/latest")
    parser.add_argument("--case", action="append", help="Run only specified scenario IDs")
    parser.add_argument("--batch", choices=("1", "2", "all"), default="all")
    args = parser.parse_args()
    CASES = (BATCH1_CASES if args.batch == "1" else BATCH2_CASES if args.batch == "2"
             else BATCH1_CASES + BATCH2_CASES)
    known = {row[0] for row in CASES}
    if args.case and not set(args.case) <= known:
        parser.error("Unknown --case; IDs: " + ", ".join(sorted(known)))
    output = Path(args.output)
    if output.exists():
        parser.error("Evidence output already exists; choose a new directory to preserve history")
    output.mkdir(parents=True)
    rows, traces = [], []
    for case_id, title, coverage, test in CASES:
        if args.case and case_id not in args.case:
            continue
        rig = BatchRig(output / "files" / case_id) if (case_id in {c[0] for c in BATCH2_CASES}) else Rig()
        status, failure = "PASS", None
        try:
            test(rig)
            if rig.ctrl.unresolved:
                status = "UNRESOLVED"
        except Exception:
            status, failure = "FAIL", traceback.format_exc()
        finally:
            if isinstance(rig, BatchRig):
                rig.cleanup()
        rows.append({"id": case_id, "title": title, "status": status,
                     "coverage": coverage, "assertions": len(rig.checks),
                     "failure": failure,
                     "unresolved_paths": rig.ctrl.unresolved})
        traces.append({"id": case_id, "status": status, "checks": rig.checks,
                       "events": rig.ctrl.trace, "observations": getattr(rig, "notes", []),
                       "failure": failure})
        print(f"{status:10} {case_id:12} {title}")
    if not args.case and args.batch != "1":
        for case_id, reason in DEFERRED.items():
            rows.append({"id": case_id, "status": "DEFERRED", "reason": reason})
            print(f"DEFERRED   {case_id:12} {reason}")
    root = Path(__file__).resolve().parent
    counts = {s: sum(r["status"] == s for r in rows)
              for s in ("PASS", "FAIL", "UNRESOLVED", "DEFERRED")}
    report = {
        "implementation_version": VERSION, "shared_baseline": BASELINE,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": platform.python_version(),
        # These fingerprints lock only source inputs that produced this evidence.
        "source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                          for p in ("controller.py", "scenarios.py", "run.py", "content_store.py",
                                    "batch2_scenarios.py", "process_worker.py")},
        "fault_threshold_ms": 1000,
        "evidence_kind": "PC_CONTROLLER_AND_FILE_PROCESS_INTERRUPTION",
        "batch": args.batch,
        "counts": counts, "cases": rows,
    }
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "traces.jsonl").open("w", encoding="utf-8") as file:
        for record in traces:
            file.write(json.dumps(record, ensure_ascii=False, default=json_default) + "\n")
    summary = [f"# RC-08 实际运行结果（batch={args.batch}）", "",
               f"实现：`{VERSION}`；Python {report['runtime']}；共同基线 `{BASELINE}`。",
               "", "虚拟音频/NFC；持久化案例使用真实PC文件与独立进程中断/重启。1000ms仅为模拟参数。", "",
               "| 场景 | 实际状态 | 覆盖/未执行原因 |", "|---|---|---|"]
    for row in rows:
        summary.append(f"| {row['id']} | {row['status']} | {row.get('coverage', row.get('reason'))} |")
    summary += ["", "计数：" + "，".join(f"{k}={v}" for k, v in counts.items()) + "。",
                "", "事件前后状态、命令/回调、断言期望/实际及失败栈见 `traces.jsonl`。",
                "`UNRESOLVED`表示已执行隔离测试但产品选择仍待决定；`DEFERRED`未执行。",
                "PC过程证据不等于SD物理掉电、音质、NFC或整机R2/硬件准入通过。"]
    (output / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("COUNTS " + json.dumps(counts))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
