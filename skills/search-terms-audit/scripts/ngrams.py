#!/usr/bin/env python3
"""Find where search-term money leaks: n-gram waste, intent classes, negative candidates.

Reads a Google Ads search terms report (UI download, any encoding, or API CSV) and prints:
  1. account summary: spend, conversions, CPA, share of spend on terms with 0 conversions
  2. n-gram table (1, 2 and 3 word pieces): spend, conversions, share of wasted spend,
     verdict NEGATIVE / REVIEW / WATCH / KEEP, example full terms
  3. intent classes (jobs, DIY, product shoppers, cheap/free, competitors, wrong service)
  4. the top individual non-converting terms

Verdicts (T = --target-cpa):
  NEGATIVE  0 conversions, spend >= T, and no converting term contains it
  REVIEW    0 conversions and spend >= T but it also appears in converting terms
            (a negative would block sales), or CPA > --kill-multiple x T
  WATCH     0 conversions, spend < T: not enough data yet, do not negate on this alone
  KEEP      converting at or near target
Brand words (--brand) are never suggested as negatives.

Examples:
  python ngrams.py search-terms.csv --target-cpa 60 --brand northwind
  python ngrams.py search-terms.csv --target-cpa 60 --csv candidates.csv   # feed negatives_check.py
  python ngrams.py search-terms.csv --target-cpa 60 --competitors "acme rooter,bluepipe" --json

Exit codes: 0 report printed, 2 bad input.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adsreport import read_report, num, norm_text  # noqa: E402

STOP = set("a an and the of for to in on at near me my with by from is are or vs best top".split())

CLASSES = [
    ("jobs", r"\b(jobs?|careers?|hiring|hire me|salary|salaries|apprentice\w*|course|courses|training|school|certification|licen[cs]e exam|resume|wage)\b"),
    ("diy", r"\b(how to|how do|diy|tutorial|youtube|video|yourself|step by step|guide)\b"),
    ("product", r"\b(for sale|parts?|buy|wholesale|rental|rent|supplies|supply|manual|amazon|ebay|kit)\b"),
    ("cheap_free", r"\b(free|cheap|cheapest|discount|coupon)\b"),
    ("research", r"\b(reviews?|vs|versus|what is|meaning|definition|types of|best)\b"),
]


def grams(words, n):
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def variants(word, vocab):
    out = []
    for v in (word + "s", word + "es", word[:-1] if word.endswith("s") else None,
              word[:-2] if word.endswith("es") else None):
        if v and v != word and v in vocab:
            out.append(v)
    return out


def analyse(rows, target, ns, brand, competitors, kill_multiple, min_cost):
    live = [r for r in rows if (r.get("added_excluded") or "").strip().lower() != "excluded"]
    excluded = len(rows) - len(live)
    terms = {}
    for r in live:
        t = norm_text(r.get("term"))
        if not t:
            continue
        d = terms.setdefault(t, {"term": t, "cost": 0.0, "clicks": 0.0, "conv": 0.0, "campaigns": set()})
        d["cost"] += num(r.get("cost"))
        d["clicks"] += num(r.get("clicks"))
        d["conv"] += num(r.get("conv"))
        if r.get("campaign"):
            d["campaigns"].add(r["campaign"])
    total_cost = sum(t["cost"] for t in terms.values())
    total_conv = sum(t["conv"] for t in terms.values())
    waste = sum(t["cost"] for t in terms.values() if t["conv"] == 0)
    if not target:
        target = total_cost / total_conv if total_conv else 0
    vocab = set(w for t in terms for w in t.split())

    g = defaultdict(lambda: {"terms": [], "cost": 0.0, "clicks": 0.0, "conv": 0.0, "waste": 0.0, "conv_terms": 0})
    for t, d in terms.items():
        words = t.split()
        for n in ns:
            for piece in set(grams(words, n)):
                pw = piece.split()
                if all(w in STOP for w in pw) or (n == 1 and len(piece) < 3):
                    continue
                s = g[piece]
                s["terms"].append(d)
                s["cost"] += d["cost"]
                s["clicks"] += d["clicks"]
                s["conv"] += d["conv"]
                if d["conv"] == 0:
                    s["waste"] += d["cost"]
                else:
                    s["conv_terms"] += 1

    out = []
    for piece, s in g.items():
        if s["cost"] < min_cost or len(s["terms"]) < 1:
            continue
        protected = any(b and b in piece for b in brand)
        cpa = s["cost"] / s["conv"] if s["conv"] else None
        if protected:
            verdict, why = "KEEP", "brand word, never a negative"
        elif s["conv"] == 0 and s["cost"] >= target:
            verdict, why = "NEGATIVE", f"spent {s['cost']:.2f} (>= target CPA) with 0 conversions"
        elif s["conv"] > 0 and s["waste"] >= target and s["waste"] / s["cost"] >= 0.5:
            verdict, why = "REVIEW", f"{s['waste']:.2f} wasted, but {s['conv_terms']} converting term(s) contain it: negate the bad terms, not the word"
        elif s["conv"] > 0 and cpa and target and cpa > kill_multiple * target:
            verdict, why = "REVIEW", f"CPA {cpa:.2f} is over {kill_multiple:g}x target"
        elif s["conv"] == 0:
            verdict, why = "WATCH", "0 conversions but spend below target CPA: not enough data"
        else:
            verdict, why = "KEEP", ""
        if verdict == "KEEP" and not protected:
            continue
        ex = sorted(s["terms"], key=lambda d: -d["cost"])[:3]
        out.append({"ngram": piece, "n": len(piece.split()), "terms": len(s["terms"]), "cost": round(s["cost"], 2),
                    "clicks": int(s["clicks"]), "conv": round(s["conv"], 2), "cpa": round(cpa, 2) if cpa else None,
                    "waste_share": round(s["waste"] / waste, 3) if waste else 0.0, "verdict": verdict, "why": why,
                    "examples": [e["term"] for e in ex], "_set": frozenset(id(d) for d in s["terms"]),
                    "variants": variants(piece, vocab) if len(piece.split()) == 1 else []})

    # mark candidates fully covered by a shorter candidate (same or superset of terms)
    negs = [o for o in out if o["verdict"] == "NEGATIVE"]
    for o in negs:
        for p in negs:
            if p is not o and p["n"] < o["n"] and o["_set"] <= p["_set"]:
                o["covered_by"] = p["ngram"]
                break
    order = {"NEGATIVE": 0, "REVIEW": 1, "WATCH": 2, "KEEP": 3}
    out.sort(key=lambda o: (order[o["verdict"]], -o["cost"]))

    classes = []
    comp = [norm_text(c) for c in competitors if c.strip()]
    for name, pat in CLASSES + [("competitor", None)]:
        if name == "competitor":
            hits = [d for t, d in terms.items() if any(c and c in t for c in comp)]
        else:
            rx = re.compile(pat)
            hits = [d for t, d in terms.items() if rx.search(t)]
        if not hits:
            continue
        c = sum(d["cost"] for d in hits)
        v = sum(d["conv"] for d in hits)
        classes.append({"class": name, "terms": len(hits), "cost": round(c, 2), "conv": round(v, 2),
                        "examples": [d["term"] for d in sorted(hits, key=lambda d: -d["cost"])[:4]]})

    top_waste = sorted([d for d in terms.values() if d["conv"] == 0], key=lambda d: -d["cost"])[:15]
    summary = {"terms": len(terms), "excluded_skipped": excluded, "cost": round(total_cost, 2),
               "conv": round(total_conv, 2), "cpa": round(total_cost / total_conv, 2) if total_conv else None,
               "target_cpa": round(target, 2), "zero_conv_cost": round(waste, 2),
               "zero_conv_share": round(waste / total_cost, 3) if total_cost else 0.0}
    return summary, out, classes, top_waste


def to_md(summary, out, classes, top_waste, top):
    p = []
    s = summary
    p.append("## Search terms audit\n")
    p.append(f"{s['terms']} terms ({s['excluded_skipped']} already excluded, skipped). Spend {s['cost']:.2f}, "
             f"conversions {s['conv']:g}, CPA {s['cpa'] if s['cpa'] is not None else 'n/a'}, target CPA used {s['target_cpa']:.2f}.")
    p.append(f"Spend on terms with 0 conversions: {s['zero_conv_cost']:.2f} ({s['zero_conv_share'] * 100:.1f}% of spend). "
             "Not all of it is waste: low-data terms land here too. The verdicts below separate them.\n")
    p.append("### N-grams\n")
    p.append("| Verdict | N-gram | Terms | Spend | Conv | CPA | Share of 0-conv spend | Why | Examples |")
    p.append("|---|---|---|---|---|---|---|---|---|")
    shown = [o for o in out if not o.get("covered_by")]
    hidden = len(out) - len(shown)
    for o in shown[:top]:
        extra = ""
        if o["variants"]:
            extra += f" add also: {', '.join(o['variants'])}"
        p.append(f"| {o['verdict']} | {o['ngram']} | {o['terms']} | {o['cost']:.2f} | {o['conv']:g} | "
                 f"{o['cpa'] if o['cpa'] is not None else '-'} | {o['waste_share'] * 100:.1f}% | {o['why']}{extra} | "
                 f"{'; '.join(o['examples'])} |")
    if hidden:
        p.append(f"\n{hidden} longer n-gram(s) hidden: a shorter NEGATIVE already covers the same terms (see --json).")
    if classes:
        p.append("\n### Intent classes\n")
        p.append("| Class | Terms | Spend | Conv | Examples |")
        p.append("|---|---|---|---|---|")
        for c in classes:
            p.append(f"| {c['class']} | {c['terms']} | {c['cost']:.2f} | {c['conv']:g} | {'; '.join(c['examples'])} |")
        p.append("\nClasses are pattern matches, not verdicts. 'research' and 'cheap_free' often convert: read the terms.")
    p.append("\n### Top non-converting terms\n")
    p.append("| Term | Spend | Clicks | Campaigns |")
    p.append("|---|---|---|---|")
    for d in top_waste:
        p.append(f"| {d['term']} | {d['cost']:.2f} | {int(d['clicks'])} | {', '.join(sorted(d['campaigns']))} |")
    p.append("\nNext: read every NEGATIVE row's example terms, then run negatives_check.py on the candidates "
             "before adding anything to the account.")
    return "\n".join(p)


def write_candidates(path, out):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Keyword", "Match type", "Level", "Reason", "Cost", "Clicks", "Conversions", "Examples"])
        for o in out:
            if o["verdict"] != "NEGATIVE" or o.get("covered_by"):
                continue
            for word in [o["ngram"]] + o["variants"]:
                w.writerow([word, "Phrase", "list: Search term mining", o["why"], o["cost"], o["clicks"], o["conv"], "; ".join(o["examples"])])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="search terms report CSV")
    ap.add_argument("--target-cpa", type=float, default=0, help="target or break-even cost per conversion (default: account CPA)")
    ap.add_argument("--n", default="1,2,3", help="n-gram sizes, default 1,2,3")
    ap.add_argument("--min-cost", type=float, default=None, help="hide n-grams below this spend (default: 25%% of target CPA)")
    ap.add_argument("--brand", default="", help="comma list of brand words that are never negatives")
    ap.add_argument("--competitors", default="", help="comma list of competitor names to group")
    ap.add_argument("--kill-multiple", type=float, default=3.0, help="REVIEW when CPA is over this multiple of target (default 3)")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--csv", metavar="FILE", help="write NEGATIVE candidates for negatives_check.py")
    a = ap.parse_args(argv)
    try:
        ns = [int(x) for x in a.n.split(",") if x.strip()]
    except ValueError:
        print("--n must look like 1,2,3", file=sys.stderr)
        return 2
    rows, _ = read_report(a.report, need=("term", "cost"))
    if not rows:
        print("no data rows", file=sys.stderr)
        return 2
    brand = [norm_text(b) for b in a.brand.split(",") if b.strip()]
    min_cost = a.min_cost if a.min_cost is not None else (a.target_cpa * 0.25 if a.target_cpa else 0)
    summary, out, classes, top_waste = analyse(rows, a.target_cpa, ns, brand, a.competitors.split(","), a.kill_multiple, min_cost)
    if a.csv:
        write_candidates(a.csv, out)
    if a.json:
        clean = [{k: v for k, v in o.items() if not k.startswith("_")} for o in out]
        tw = [{"term": d["term"], "cost": round(d["cost"], 2), "clicks": d["clicks"], "campaigns": sorted(d["campaigns"])} for d in top_waste]
        print(json.dumps({"summary": summary, "ngrams": clean, "classes": classes, "top_waste": tw}, indent=2))
    else:
        print(to_md(summary, out, classes, top_waste, a.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
