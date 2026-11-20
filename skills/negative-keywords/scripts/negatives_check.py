#!/usr/bin/env python3
"""Check negative keywords before they go live: what they block, what they break.

Simulates negative matching on your search terms and positive keywords:
  * exact    [x]   blocks a term only when the term is exactly x (word order matters)
  * phrase   "x"   blocks a term containing the words of x in that order
  * broad     x    blocks a term containing all words of x in any order
Negatives do NOT expand to plurals, synonyms or close variants (Google help: "About
negative keywords"). Casing and most misspellings are handled by Google, plurals are not,
so the script lists plural and singular forms that appear in your terms or keywords.

Flags:
  HARMFUL    a negative blocks a term that converted, or a positive keyword's own text
  NO_EFFECT  a negative matches nothing in the report (fine for prevention, but check spelling)
  COVERAGE   how much 0-conversion spend the list would have blocked
  LIMITS     warns when a list nears the per-list or per-campaign caps (check current limits)

Inputs:
  negatives CSV with columns Keyword, Match type (optional if [x] / "x" notation), Level (optional)
  --terms   search terms report (to measure waste blocked and conversions blocked)
  --keywords keyword report (to catch negatives that block your own keywords)
  --editor FILE  write a Google Ads Editor style CSV of the safe negatives

Examples:
  python negatives_check.py candidates.csv --terms search-terms.csv --keywords keywords.csv
  python negatives_check.py negatives.csv --terms search-terms.csv --editor upload.csv

Exit codes: 0 no harmful negatives, 1 harmful negatives found, 2 bad input.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adsreport import read_report, num, norm_text, match_type_of  # noqa: E402

LIST_CAP = 5000        # negatives per shared list (Google help, check current)
CAMPAIGN_CAP = 10000   # negatives per campaign (Google help, check current)


def blocks(neg_words, mt, term_words):
    if mt == "exact":
        return term_words == neg_words
    if mt == "phrase":
        n = len(neg_words)
        return any(term_words[i:i + n] == neg_words for i in range(len(term_words) - n + 1))
    return set(neg_words) <= set(term_words)


def forms(word):
    out = []
    if word.endswith("ies") and len(word) > 4:
        out.append(word[:-3] + "y")
    elif word.endswith("es") and len(word) > 3 and word[-3] in "sxzh":
        out.append(word[:-2])
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        out.append(word[:-1])
    else:
        out.append(word[:-1] + "ies" if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou"
                   else word + ("es" if word[-1] in "sxzh" else "s"))
    return out


def load_negatives(path):
    rows, _ = read_report(path, need=("keyword",))
    negs = []
    for r in rows:
        text, mt = match_type_of(r.get("keyword"), r.get("match_type"))
        if not text:
            continue
        negs.append({"text": text, "match": mt, "level": r.get("level") or "", "words": text.split()})
    return negs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("negatives")
    ap.add_argument("--terms", help="search terms report")
    ap.add_argument("--keywords", help="keyword report (positive keywords)")
    ap.add_argument("--editor", metavar="FILE", help="write safe negatives as an Editor style CSV")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    negs = load_negatives(a.negatives)
    if not negs:
        print("no negatives found", file=sys.stderr)
        return 2
    terms = []
    if a.terms:
        rows, _ = read_report(a.terms, need=("term", "cost"))
        for r in rows:
            if (r.get("added_excluded") or "").lower() == "excluded":
                continue
            t = norm_text(r.get("term"))
            terms.append({"term": t, "words": t.split(), "cost": num(r.get("cost")), "conv": num(r.get("conv")),
                          "campaign": r.get("campaign") or ""})
    kws = []
    if a.keywords:
        rows, _ = read_report(a.keywords, need=("keyword",))
        for r in rows:
            text, mt = match_type_of(r.get("keyword"), r.get("match_type"))
            kws.append({"text": text, "words": text.split(), "campaign": r.get("campaign") or "", "conv": num(r.get("conv"))})

    vocab = {w for t in terms for w in t["words"]} | {w for k in kws for w in k["words"]}
    zero_cost = sum(t["cost"] for t in terms if t["conv"] == 0)
    blocked_terms = set()
    results = []
    for n in negs:
        hit = [t for t in terms if blocks(n["words"], n["match"], t["words"])]
        conv_hit = [t for t in hit if t["conv"] > 0]
        kw_hit = [k for k in kws if blocks(n["words"], n["match"], k["words"])]
        for t in hit:
            if t["conv"] == 0:
                blocked_terms.add(t["term"])
        flags = []
        if conv_hit:
            flags.append("HARMFUL: blocks converting term(s) " + "; ".join(f"{t['term']} ({t['conv']:g} conv)" for t in conv_hit[:3]))
        if kw_hit:
            flags.append("HARMFUL: blocks your keyword(s) " + "; ".join(k["text"] for k in kw_hit[:3]))
        if terms and not hit:
            flags.append("NO_EFFECT in this report")
        missing_forms = []
        if n["match"] != "exact":
            existing = {x["text"] for x in negs}
            for w in n["words"]:
                for f in forms(w):
                    if vocab and f not in vocab:
                        continue   # only suggest forms people actually searched
                    alt = " ".join(f if x == w else x for x in n["words"])
                    if alt not in existing:
                        missing_forms.append(alt)
        results.append({"negative": n["text"], "match": n["match"], "level": n["level"],
                        "blocked_terms": len(hit), "blocked_cost": round(sum(t["cost"] for t in hit), 2),
                        "blocked_conv": round(sum(t["conv"] for t in hit), 2),
                        "harmful": any(f.startswith("HARMFUL") for f in flags), "flags": flags,
                        "add_forms": missing_forms, "examples": [t["term"] for t in sorted(hit, key=lambda t: -t["cost"])[:3]]})

    covered = sum(t["cost"] for t in terms if t["term"] in blocked_terms)
    by_level = {}
    for n in negs:
        by_level[n["level"] or "(no level)"] = by_level.get(n["level"] or "(no level)", 0) + 1
    limits = [f"{lvl}: {c} negatives, near the per-list cap of {LIST_CAP}" for lvl, c in by_level.items()
              if lvl.lower().startswith("list") and c > LIST_CAP * 0.8]
    limits += [f"{lvl}: {c} negatives, near the per-campaign cap of {CAMPAIGN_CAP}" for lvl, c in by_level.items()
               if lvl.lower().startswith("campaign") and c > CAMPAIGN_CAP * 0.8]
    harmful = [r for r in results if r["harmful"]]

    if a.editor:
        with open(a.editor, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Campaign", "Ad group", "Keyword", "Criterion Type", "Shared set name (verify)", "Note"])
            for r in results:
                if r["harmful"]:
                    continue
                kw = f"[{r['negative']}]" if r["match"] == "exact" else (f'"{r["negative"]}"' if r["match"] == "phrase" else r["negative"])
                lvl = r["level"]
                camp = lvl.split(":", 1)[1].strip() if lvl.lower().startswith("campaign") else ""
                shared = lvl.split(":", 1)[1].strip() if lvl.lower().startswith("list") else ""
                w.writerow([camp, "", kw, f"Negative {r['match']}", shared,
                            "column names differ between Editor versions: map them on import"])

    if a.json:
        print(json.dumps({"negatives": results, "zero_conv_spend": round(zero_cost, 2), "covered": round(covered, 2),
                          "limits": limits}, indent=2))
    else:
        print("## Negative keyword check\n")
        print(f"{len(negs)} negatives checked against {len(terms)} search terms and {len(kws)} keywords.")
        if terms:
            share = covered / zero_cost * 100 if zero_cost else 0
            print(f"Would have blocked {covered:.2f} of {zero_cost:.2f} zero-conversion spend ({share:.0f}%).\n")
        print("| Negative | Match | Level | Terms blocked | Spend blocked | Conv blocked | Flags | Add forms |")
        print("|---|---|---|---|---|---|---|---|")
        for r in sorted(results, key=lambda r: (not r["harmful"], -r["blocked_cost"])):
            print(f"| {r['negative']} | {r['match']} | {r['level']} | {r['blocked_terms']} | {r['blocked_cost']:.2f} | "
                  f"{r['blocked_conv']:g} | {' / '.join(r['flags']) or 'ok'} | {', '.join(r['add_forms'])} |")
        for l in limits:
            print(f"\nLIMITS: {l}")
        if harmful:
            print(f"\n{len(harmful)} HARMFUL negative(s). Remove or narrow them (phrase to exact, or a longer phrase) before upload.")
        else:
            print("\nNo harmful negatives found in this data. Data only covers terms you already paid for: "
                  "a negative can still block future good searches.")
    return 1 if harmful else 0


if __name__ == "__main__":
    sys.exit(main())
