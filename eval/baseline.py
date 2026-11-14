"""Mine certified findings, optionally verify/export/score neutral answers.

    python -m eval.baseline --facts evidence/case_facts.json \
        --certs runs/dev/miner/certs --run runs/dev/miner/run.json \
        --out runs/dev/miner/results.json --questions eval/benchmark_nist_questions.json \
        --reference eval/benchmark_nist.json --adapter nist

No answer key or labeled claim helps select mined findings. Gate probes are optional,
explicit and kept in a separate directory. Every output path must be new.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.case import select_case, read_question_profile, with_questions
from checker import export, report
from checker.facts import open_source
from eval import gate, pipeline
from miner import mine as miner


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--facts", default="evidence/case_facts.json")
    ap.add_argument("--certs", default="runs/dev/miner/certs")
    ap.add_argument("--run", default="runs/dev/miner/run.json")
    ap.add_argument("--out", default="runs/dev/miner/results.json")
    ap.add_argument("--case-profile", help="public case context; no expected answers")
    ap.add_argument("--questions", help="public schema-v2 question/answer-shape profile")
    ap.add_argument("--reference", help="explicit private schema-v2 evaluation reference")
    answers = ap.add_mutually_exclusive_group()
    answers.add_argument("--adapter", choices=("nist",))
    answers.add_argument("--answers", help="external structured answers for another case or system")
    probes = ap.add_mutually_exclusive_group()
    probes.add_argument("--labeled-claims", help="explicit false-claim gate regression fixture")
    probes.add_argument("--no-gate", action="store_true", help="do not measure gate regression")
    ap.add_argument("--no-score", action="store_true")
    ap.add_argument("--complete", action="store_true", help="include large record kinds and journal identity joins")
    args = ap.parse_args(argv)
    certs, run, output = Path(args.certs), Path(args.run), Path(args.out)
    answers_output = output.with_name("answers.json")
    verification_output = output.with_name("verification.json")
    report_output = run.with_name("report.md")
    try:
        profile, profile_source = select_case(Path(args.facts),
                                               Path(args.case_profile) if args.case_profile else None)
        if args.questions:
            profile = with_questions(profile, read_question_profile(args.questions))
            profile_source += "+questions"
        plan = pipeline.prepare(args.reference, args.questions, args.adapter, args.answers,
                                profile.case_id, args.no_score)
        if args.labeled_claims:
            gate.load_fixture(args.labeled_claims, profile.case_id, profile.time_zone)
        paths = [certs, run, output, answers_output, verification_output, report_output]
        if len({p.resolve() for p in paths}) != len(paths):
            raise ValueError("output paths must be distinct")
        for path in paths:
            if path.exists() or path.is_symlink():
                raise ValueError(f"refusing to overwrite existing output: {path}; choose a new path")
        for a in paths:
            for b in paths:
                if a != b and a != certs and a.resolve() in b.resolve().parents:
                    raise ValueError("output file paths cannot contain another output")
    except (ValueError, OSError) as error:
        ap.error(str(error))
    source = open_source(args.facts)
    skipped = miner.skipped_kinds(source, complete=args.complete)
    if skipped:
        print(f"bounded mode omits one-record statements for {skipped}; use --complete to include them")
        if set(skipped) & {"journalName", "journalParent", "journalRemoval", "journalPath"}:
            print("bounded mode also omits compound journal identity joins")
    # Reserve the certificate directory, including empty runs, without replacing prior data.
    certs.mkdir(parents=True, exist_ok=False)
    mined = miner.mine(source, certs, complete=args.complete)
    print(f"miner: {len(mined)} candidates, {sum(r['status'] == 'verified' for r in mined)} certified")
    regression = gate.measure(args.labeled_claims, source, profile.case_id, profile.time_zone,
                              certs / "gate-probes") if args.labeled_claims else None
    data = export.bundle(certs, profile.name)
    data["case"].update(case_id=profile.case_id, time_zone=profile.time_zone,
                        profile_source=profile_source,
                        mining={"complete": args.complete, "omitted_one_record_kinds": skipped})
    run.parent.mkdir(parents=True, exist_ok=True)
    with run.open("x") as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    with report_output.open("x") as stream:
        stream.write(report.render(data))
    try:
        pipeline.evaluate(plan, data, answers_output, output, regression,
                          facts_path=args.facts, verification_output=verification_output)
    except (ValueError, OSError) as error:
        ap.error(str(error))
    return 1 if regression and not regression["all_as_expected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
