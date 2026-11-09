# AntiVenom tool

Turn one caught poisoned record into a small **claim signature** that protects every agent's retrieved context. Receivers remove passages that assert the claim, whatever they are named or however they are worded, and act only when the claim is present.

> **Status.** Research prototype, version 0.1. It implements the method evaluated in the AntiVenom report (PoisonedRAG, Qwen2.5-7B). It is not yet tested in production or against adaptive attackers. Written on 4 November 2026, before the Apart Swarm Alignment Hackathon, so it is **preexisting work** for that sprint.

## Install

```bash
pip install ./tool                 # core: no dependencies
pip install "./tool[nli]"          # adds the paper's local NLI model (sentence-transformers)
```

Python 3.9 or later. Without the `nli` extra, use an LLM judge for entailment (see below).

## Two calls

```python
from antivenom_tool import make_signature, Defender, OpenAICompatibleLLM

llm = OpenAICompatibleLLM("openai/gpt-4o-mini")          # any OpenAI-compatible endpoint; key from OPENROUTER_API_KEY
sig = make_signature(caught_record_text, llm)              # the finder: ~250-byte signature
report = Defender([sig]).check(passages, query)            # each receiver
answer_with(report.kept)
```

`report` lists, for every passage, whether it was flagged, its entailment score, and a plain reason. With `refill=fn`, removed passages are replaced by `fn(n)` (for example your next-ranked results), and replacements are checked too. If the LLM returns no claim, `make_signature` raises `ExtractionError` rather than producing a useless signature. `Signature.manual(question, claim)` builds one without an LLM.

## Use it in any harness

| Harness | How |
|---|---|
| Any Python loop | `guard_retriever(my_search, defender)` wraps `my_search(query, k)` and refills from extra results |
| LangChain-style retrievers | `GuardedRetriever(retriever, defender)`; returns the same document objects minus flagged ones |
| LlamaIndex-style nodes | `filter_nodes(nodes, defender, query)` inside a node postprocessor |
| Any language or shell | the `antivenom` CLI reads and writes JSON |
| Claude, Cursor or any MCP client | the built-in MCP server (stdio, no dependencies) |

Adapters use duck typing, so no framework is imported. Anything with `page_content`, `text`, `content` or `get_content()` works.

### Command line

```bash
antivenom signature --record caught.txt --llm-model openai/gpt-4o-mini > sig.json
antivenom signature --question "What is the main industry in the Canadian Shield?" --claim "fishing" > sig.json
antivenom check --signatures sig.json --passages passages.json --query "..."     # JSON report
```

### MCP server

```bash
claude mcp add antivenom -- python -m antivenom_tool.mcp_server --llm-model openai/gpt-4o-mini
```

Tools: `make_signature`, `add_signature`, `check_passages`, `list_signatures`, `revoke_signature`. Add `--registry signatures.json` (with `ANTIVENOM_KEY` set) to persist and share signatures.

## Sharing across a swarm

A forged signature could make agents delete good evidence, so shared signatures are signed with a shared key (HMAC-SHA256), can expire, and can be revoked.

```python
from antivenom_tool import SignatureRegistry
reg = SignatureRegistry(path="signatures.json")       # key from ANTIVENOM_KEY
reg.publish(sig)                                        # finder
message = reg.export()[0]                               # send over any transport
other_registry.ingest(message)                          # receiver: rejects bad MACs, expired or revoked signatures
guarded = guard_retriever(search, Defender([]), registry=other_registry)   # picks up new signatures on every call
```

## Choosing backends

| Role | Options |
|---|---|
| Signature extraction | `OpenAICompatibleLLM` (OpenRouter, OpenAI, vLLM, Ollama, LM Studio), `CallableLLM(fn)` |
| Claim check | `CrossEncoderEntailment()` (paper default, local), `LLMJudgeEntailment(llm)` (any API model) |
| Second signal (optional) | `attention=` any `fn(query, passages) -> z-scores`; `antivenom_tool.attention.mlx_attention()` for local MLX models, or a counterfactual influence score for API models |

Defaults come from the paper's calibration: flag at entailment ≥ 0.01; with a second signal, combined score ≥ 0.0989; gate at entailment ≥ 0.975. Thresholds were fitted for DeBERTa-v3 NLI and Qwen2.5-7B attention. Recalibrate on your own clean data when you change backends.

## Tests

```bash
python -m unittest discover -s tool/tests                          # 18 unit tests, stand-in models, no downloads
HF_HUB_OFFLINE=1 .venv/bin/python tool/tests/integration_real.py   # real NLI on released PoisonedRAG data
```

The integration test reproduces the paper's decisions for NQ question test363. Four of five planted passages are flagged by the claim check, all clean passages are kept, and the CLI agrees.

## Limits

- Detection quality depends on the extraction model. Small models can return blank claims; the tool raises an error instead of continuing.
- The attention signal needs model internals, so it is unavailable through APIs.
- Thresholds are calibrated on one benchmark of near-duplicate poisons. The attacker in the evaluation does not adapt.
- The registry signs messages but does not provide transport, identity or key distribution.
