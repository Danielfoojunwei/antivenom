"""Command line: JSON in, JSON out, so any harness or language can use it.

  antivenom signature --record caught.txt [--llm-model M | --question Q --claim C]
  antivenom check --signatures sigs.json --passages passages.json [--query Q] [--judge --llm-model M]
  antivenom publish --registry reg.json --signature sig.json      (needs ANTIVENOM_KEY)
  antivenom list --registry reg.json
  antivenom revoke --registry reg.json --id ID
  antivenom mcp [server options]

Files may be '-' for stdin. ``--signatures`` accepts one signature object,
a list of them, or a registry file.
"""
from __future__ import annotations

import argparse
import json
import sys

from .backends import CrossEncoderEntailment, LLMJudgeEntailment, OpenAICompatibleLLM
from .defender import Defender
from .registry import SignatureRegistry
from .signature import Signature, make_signature


def _read(path: str) -> str:
    return sys.stdin.read() if path == "-" else open(path).read()


def _sigs(path: str) -> list[Signature]:
    d = json.loads(_read(path))
    if isinstance(d, dict) and "messages" in d:
        return SignatureRegistry(path=path).active()
    if isinstance(d, dict):
        d = [d]
    return [Signature.from_dict(x.get("signature", x)) for x in d]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="antivenom", description="AntiVenom: share what a poison says, not where it is.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("signature"); s.add_argument("--record"); s.add_argument("--question"); s.add_argument("--claim")
    s.add_argument("--llm-model"); s.add_argument("--base-url", default="https://openrouter.ai/api/v1"); s.add_argument("--ttl", type=float)
    c = sub.add_parser("check"); c.add_argument("--signatures", required=True); c.add_argument("--passages", required=True)
    c.add_argument("--query", default=""); c.add_argument("--no-gate", action="store_true")
    c.add_argument("--judge", action="store_true"); c.add_argument("--llm-model"); c.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    p = sub.add_parser("publish"); p.add_argument("--registry", required=True); p.add_argument("--signature", required=True)
    l = sub.add_parser("list"); l.add_argument("--registry", required=True)
    r = sub.add_parser("revoke"); r.add_argument("--registry", required=True); r.add_argument("--id", required=True)
    sub.add_parser("mcp", add_help=False)
    a, rest = ap.parse_known_args(argv)

    if a.cmd == "mcp":
        from .mcp_server import main as mcp_main
        return mcp_main(rest)
    if a.cmd == "signature":
        if a.question and a.claim:
            sig = Signature.manual(a.question, a.claim)
        else:
            if not (a.record and a.llm_model):
                ap.error("give --record and --llm-model, or --question and --claim")
            sig = make_signature(_read(a.record), OpenAICompatibleLLM(a.llm_model, base_url=a.base_url), ttl_seconds=a.ttl)
        print(sig.to_json())
    elif a.cmd == "check":
        passages = json.loads(_read(a.passages))
        ent = LLMJudgeEntailment(OpenAICompatibleLLM(a.llm_model, base_url=a.base_url)) if a.judge else CrossEncoderEntailment()
        rep = Defender(_sigs(a.signatures), entailment=ent, gate=not a.no_gate).check(passages, a.query)
        print(json.dumps(rep.to_dict(), indent=1))
    elif a.cmd == "publish":
        print(json.dumps(SignatureRegistry(path=a.registry).publish(_sigs(a.signature)[0])))
    elif a.cmd == "list":
        print(json.dumps([x.to_dict() for x in SignatureRegistry(path=a.registry).active()], indent=1))
    elif a.cmd == "revoke":
        SignatureRegistry(path=a.registry).revoke(a.id); print(json.dumps({"revoked": a.id}))


if __name__ == "__main__":
    main()
