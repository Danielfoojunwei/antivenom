"""Family-paired external diagnostic with fixed, undefended eligibility."""
import itertools
import json
from pathlib import Path

from antivenom.continuation import read_rows, save
from antivenom.memform_port import family_split, native_functions
from antivenom.incident import sha
from continuation_stats import holm
from incident_summary import estimate, difference


def main():
    data = [json.loads(x) for x in open("data/external/memform/accepted_mcq.jsonl")]
    families, cal, test = family_split(data)
    rows = read_rows("results/incident_memform.jsonl")
    assert len(rows) == 212 and {r["id"] for r in rows} == set(test)
    native = native_functions()
    flat, eligible = [], []
    all_arms = sorted(rows[0]["answers"])
    for r in rows:
        assert sorted(r["answers"]) == all_arms
        tasks = families[r["id"]]["P2"]["evaluation"]["trigger_tasks"]
        case = families[r["id"]]["P2"]
        sample = families[r["id"]]["P1"]["memory_building"]["poisoned_condition"]["memory_text"]
        assert r["artifact"]["sample_sha256"] == sha(sample)
        mapping = native["exp_texts"](case)
        for arm, result in r["answers"].items():
            condition = arm.split(":",1)[0]
            texts = [mapping[i] for i in case["memory_building"][condition+"_condition"]["evidence_ids"]]
            assert result["input_hashes"] == [sha(t) for t in texts]
            assert result["kept_hashes"] == [sha(t) for i,t in enumerate(texts) if i not in result["flags"]]
            assert sample not in texts
        for task in tasks:
            tid = task["task_id"]
            baseline = r["no_memory"][tid]
            clean_none = r["answers"]["clean:none"]["tasks"][tid]
            is_eligible = task["clean_answer"] != task["poisoned_answer"] and baseline["correct"] and clean_none["correct"]
            item = {"target_id": r["id"], "answers": {}}
            for arm in all_arms:
                decision = r["answers"][arm]["tasks"][tid]
                pred, parser = native["parse_final_label_details"](decision["resp"], [c["label"] for c in task["choices"]])
                assert pred == decision["prediction"] and parser == decision["parse_method"]
                assert decision["correct"] == (pred == task["clean_answer"])
                assert decision["endorsed"] == (pred == task["poisoned_answer"])
                item["answers"][arm] = decision
            flat.append(item)
            if is_eligible: eligible.append(item)
    def report(scope):
        if not scope: return {"tasks": 0, "families": 0, "rates": {}, "comparisons": {}}
        rates = {}
        def grouped(arm, metric):
            by = {}
            for row in scope: by.setdefault(row["target_id"], []).append(float(row["answers"][arm][metric]))
            return {k: sum(v)/len(v) for k,v in by.items()}
        for arm in all_arms:
            rates[arm] = {m: estimate(grouped(arm,m).values()) for m in ("correct", "endorsed")}
            rates[arm]["parse_failure_rate"] = sum(r["answers"][arm]["prediction"] is None for r in scope)/len(scope)
        methods = sorted(a.split(":",1)[1] for a in all_arms if a.startswith("clean:"))
        comparisons = {}
        for a,b in itertools.combinations(methods,2):
            for condition in ("clean", "poisoned"):
                for metric in ("correct", "endorsed"):
                    comparisons[f"{condition}:{a}-{b}:{metric}"] = difference(grouped(condition+":"+a,metric), grouped(condition+":"+b,metric), len(scope) != len({r['target_id'] for r in scope}))
        adjusted = holm({k:v["p"] for k,v in comparisons.items()})
        for k,v in comparisons.items(): v["holm_p"] = adjusted[k]
        return {"tasks": len(scope), "families": len({r["target_id"] for r in scope}), "rates":rates,"comparisons":comparisons}
    result = {"scope":"MemForm P1-capture to P2-forged-history local port; not MemMorph or primary confirmation",
              "all_tasks":report(flat), "fixed_causal_eligible":report(eligible),
              "eligibility":"Distinct action labels AND correct no-memory AND correct undefended clean-memory; identical denominator for every defence",
              "holm_family":"All pairs, both memory conditions and both action endpoints within each reported scope",
              "limitations":["TrustRAG comparator is its document filter only, followed by the common native memory compiler",
                            "One reader, one external interface; no claim of all-interface robustness or full TrustRAG equivalence"]}
    save("results/incident_memform_summary.json",result)
    save("results/incident_memform_integrity.json",{"passed":True,"families":len(rows),"calibration_families":len(cal),"eligible_tasks":len(eligible)})
    Path("results/rescored/summaries/incident_memform.txt").write_text(json.dumps(result,indent=2)+"\n")
    print("MemForm diagnostic validated:",len(rows),"held-out families; causal-eligible tasks:",len(eligible))


if __name__ == "__main__": main()
