"""E21 worst-case capture: entailment recall/FPR (tau=0.01) per captured poison
index, worst-case over indices per target, and the any-of-5 k-capture row.
Recall excludes the captured passage itself. j=0 from E11a."""
import json
import numpy as np
TAU = 0.01
e11 = {json.loads(l)["id"]: json.loads(l) for l in open("results/e11a_flag_scores_nq_k10.jsonl")}
rows = [json.loads(l) for l in open("results/e21_capture_rotation_nq_k10.jsonl")]
per = {j: [0, 0, 0, 0] for j in range(5)}  # tp, P, fp, N
worst, anyk = [], [0, 0, 0, 0]
for r in rows:
    pidx = r["poison_index"]
    caps = {0: e11[r["id"]]["entail_qa"], **{int(k): v["entail"] for k, v in r["captures"].items()}}
    rec_t = []
    for j, ent in caps.items():
        if j not in pidx:
            continue  # captured poison not in top-10
        cap_slot = pidx.index(j)
        P = [i for i, p in enumerate(pidx) if p >= 0 and i != cap_slot]
        N = [i for i, p in enumerate(pidx) if p < 0]
        tp = sum(ent[i] >= TAU for i in P); fp = sum(ent[i] >= TAU for i in N)
        per[j][0] += tp; per[j][1] += len(P); per[j][2] += fp; per[j][3] += len(N)
        if P:
            rec_t.append(tp / len(P))
    if rec_t:
        worst.append(min(rec_t))
    N = [i for i, p in enumerate(pidx) if p < 0]; P = [i for i, p in enumerate(pidx) if p >= 0]
    mx = np.max([caps[j] for j in caps], 0)
    anyk[0] += sum(mx[i] >= TAU for i in P); anyk[1] += len(P); anyk[2] += sum(mx[i] >= TAU for i in N); anyk[3] += len(N)
print(f"E21 capture rotation, NQ dev n={len(rows)} (entailment flags only, tau={TAU})")
for j, (tp, P, fp, N) in per.items():
    print(f"  capture poison[{j}]  recall {tp/P:.3f}  FPR {fp/N:.3f}")
print(f"  per-target worst capture: mean recall {np.mean(worst):.3f}; targets with worst recall < 0.5: {sum(w < .5 for w in worst)}/{len(worst)}")
print(f"  any-of-5 captured (k-capture threat model, includes captured slots): recall {anyk[0]/anyk[1]:.3f} FPR {anyk[2]/anyk[3]:.3f}")
