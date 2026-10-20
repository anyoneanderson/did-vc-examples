#!/usr/bin/env python3
"""Check preparation data only; never issue or verify credentials."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def main():
    fixture = load("fixtures/training-completion.json")
    plan = load("fixtures/cases.json")
    status = load("results/implementation-status.json")
    template = load("results/run-template.json")
    require(fixture["kind"] == "unsigned-business-fixture", "fixture must be unsigned business data")
    require(plan["scenarioId"] == fixture["scenarioId"], "scenario mismatch")
    claims = fixture["claims"]
    require(set(claims) == {"name", "courseId", "completedOn", "email"}, "unexpected claim set")
    require(all(isinstance(v, str) and v for v in claims.values()), "claims must be nonempty strings")
    date.fromisoformat(claims["completedOn"])
    require(claims["email"].endswith("@example.com"), "use fictional email")
    presentation = fixture["presentation"]
    disclosed = set(presentation["requiredClaims"])
    hidden = set(presentation["undisclosedClaims"])
    require(not disclosed & hidden and disclosed | hidden == set(claims), "invalid disclosure partition")
    require(hidden == {"email"}, "email must remain undisclosed")
    require(presentation["holderBindingRequired"] is True, "holder binding required by this scenario")
    acceptance = fixture["acceptance"]
    require(fixture["issuer"]["id"] in acceptance["acceptedIssuerIds"], "happy-path issuer not accepted")
    require(claims["courseId"] in acceptance["acceptedCourseIds"], "happy-path course not accepted")
    require(claims["name"] == acceptance["expectedApplicantName"], "applicant mismatch")
    times = fixture["timingSecondsRelativeToT0"]
    require(times["valid"]["issuedAt"] <= 0 < times["valid"]["expiresAt"], "invalid normal time offsets")
    require(times["expired"]["issuedAt"] < times["expired"]["expiresAt"] < 0, "invalid expired time offsets")
    ids = [c["id"] for c in plan["cases"]]
    required = {"happy-path", "tampered-claim", "expired", "wrong-holder-key", "untrusted-issuer", "missing-required-claim", "wrong-course", "wrong-nonce", "wrong-audience", "missing-key-binding"}
    require(len(ids) == len(set(ids)) and set(ids) == required, "missing or duplicate planned cases")
    for case in plan["cases"]:
        require(case["setup"] and case["targetCheck"], "missing case description")
        require(case["expectedDecision"] == ("ACCEPT" if case["id"] == "happy-path" else "REJECT"), "unexpected decision")
    implementations = status["implementations"]
    require(len(implementations) == 2 and {i["id"] for i in implementations} == {"walt-id", "procivis-one"}, "implementation mismatch")
    for group in [i["cases"] for i in implementations] + [template["cases"]]:
        require(len(group) == len(ids) and {c["caseId"] for c in group} == set(ids), "result coverage mismatch")
        for case in group:
            require(case["executionStatus"] == "NOT_RUN" and case["actualDecision"] is None and case["evidence"] == [], "preparation must not claim runtime results")
    print(f"PASS: fixture consistency ({len(claims)} claims, {len(ids)} planned cases, {len(implementations)} implementations)")
    print("NOTE: no credential issuance, signature verification, or OSS integration was run.")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
