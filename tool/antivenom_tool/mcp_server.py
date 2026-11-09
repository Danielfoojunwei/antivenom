"""Model Context Protocol server (stdio, JSON-RPC 2.0), no dependencies.

Any MCP client (Claude Desktop, Claude Code, Cursor, custom agents) can call:
  make_signature   turn a caught poisoned record into a claim signature
  add_signature    activate a signature (plain or signed message)
  check_passages   score passages; return kept / removed with reasons
  list_signatures  show active signatures
  revoke_signature deactivate one

Run:  python -m antivenom_tool.mcp_server  [--llm-model M] [--base-url URL] [--registry PATH]
Signatures persist in the registry file when --registry is given (key: ANTIVENOM_KEY).
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import __version__
from .backends import CrossEncoderEntailment, LLMJudgeEntailment, OpenAICompatibleLLM
from .defender import Defender
from .registry import SignatureRegistry
from .signature import Signature, make_signature

PROTOCOL = "2024-11-05"

TOOLS = [
    {"name": "make_signature", "description": "Turn one caught poisoned record into a shareable claim signature (question + false claim). Give either 'record' (uses the configured LLM) or both 'question' and 'claim'. The signature is activated.",
     "inputSchema": {"type": "object", "properties": {"record": {"type": "string"}, "question": {"type": "string"}, "claim": {"type": "string"},
                                                      "ttl_seconds": {"type": "number"}}}},
    {"name": "add_signature", "description": "Activate a signature received from another agent: a plain signature object, or a signed registry message {signature, mac}.",
     "inputSchema": {"type": "object", "properties": {"signature": {"type": "object"}, "message": {"type": "object"}}}},
    {"name": "check_passages", "description": "Check retrieved passages against active signatures. Returns kept and removed passages with a reason for each.",
     "inputSchema": {"type": "object", "properties": {"passages": {"type": "array", "items": {"type": "string"}}, "query": {"type": "string"}},
                     "required": ["passages"]}},
    {"name": "list_signatures", "description": "List active signatures.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "revoke_signature", "description": "Deactivate a signature by id.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]


class Server:
    def __init__(self, llm=None, entailment=None, registry: SignatureRegistry | None = None):
        self.llm, self.registry = llm, registry
        self.defender = Defender(registry.active() if registry else (), entailment=entailment)

    def _activate(self, sig: Signature) -> dict:
        if self.registry:
            msg = self.registry.publish(sig)
        else:
            msg = None
        self.defender.add(sig)
        return {"signature": sig.to_dict(), "signed_message": msg}

    def call(self, name: str, a: dict) -> dict:
        if self.registry:
            for s in self.registry.refresh():
                self.defender.add(s)
        if name == "make_signature":
            if a.get("question") and a.get("claim"):
                sig = Signature.manual(a["question"], a["claim"])
            else:
                if not self.llm:
                    raise ValueError("no LLM configured: start the server with --llm-model, or pass question and claim")
                sig = make_signature(a["record"], self.llm, ttl_seconds=a.get("ttl_seconds"))
            return self._activate(sig)
        if name == "add_signature":
            if a.get("message"):
                if not self.registry:
                    raise ValueError("signed messages need --registry and ANTIVENOM_KEY")
                sig = self.registry.ingest(a["message"])
                self.defender.add(sig)
                return {"signature": sig.to_dict()}
            return self._activate(Signature.from_dict(a["signature"]))
        if name == "check_passages":
            return self.defender.check(a["passages"], a.get("query", "")).to_dict()
        if name == "list_signatures":
            return {"signatures": [s.to_dict() for s in self.defender.active()]}
        if name == "revoke_signature":
            self.defender.remove(a["id"])
            if self.registry:
                self.registry.revoke(a["id"])
            return {"revoked": a["id"]}
        raise ValueError(f"unknown tool {name}")

    def handle(self, req: dict) -> dict | None:
        m, rid = req.get("method"), req.get("id")
        if rid is None:                       # notification
            return None
        try:
            if m == "initialize":
                res = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                       "serverInfo": {"name": "antivenom", "version": __version__}}
            elif m == "tools/list":
                res = {"tools": TOOLS}
            elif m == "tools/call":
                p = req.get("params", {})
                try:
                    out = self.call(p.get("name"), p.get("arguments") or {})
                    res = {"content": [{"type": "text", "text": json.dumps(out)}], "isError": False}
                except Exception as e:  # tool errors are reported to the client, not raised
                    res = {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
            elif m == "ping":
                res = {}
            else:
                return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {m}"}}
            return {"jsonrpc": "2.0", "id": rid, "result": res}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": str(e)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--llm-model"); ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--judge", action="store_true", help="use the LLM as entailment judge instead of the local NLI model")
    ap.add_argument("--registry")
    a = ap.parse_args(argv)
    llm = OpenAICompatibleLLM(a.llm_model, base_url=a.base_url) if a.llm_model else None
    ent = LLMJudgeEntailment(llm) if (a.judge and llm) else CrossEncoderEntailment()
    srv = Server(llm, ent, SignatureRegistry(path=a.registry) if a.registry else None)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = srv.handle(json.loads(line))
        except Exception:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": traceback.format_exc(limit=1)}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()
