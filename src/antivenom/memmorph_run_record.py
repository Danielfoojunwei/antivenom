"""Bind reported MemMorph evaluation records without running models or tools.

These hashes bind reported records to supplied inputs. They do not authenticate
native provenance, actual execution, parser correctness, or independence. The
inert integration helper uses a whitelisted selection-input projection, NOT an
unknown native prompt. Its fixtures are software checks, never native efficacy.
This new module does not amend the frozen v1 preparation or completed studies.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from numbers import Real
from typing import Any, Callable, Mapping, Sequence

MANIFEST_SCHEMA = "antivenom.memmorph.bound-run.v1"
REQUEST_SCHEMA = "antivenom.memmorph.bound-request.v1"
OBSERVATION_SCHEMA = "antivenom.memmorph.bound-observation.v1"
WARNING = ("Hashes bind reported records only; they do not authenticate native "
           "provenance, actual model execution, parser correctness, or independence.")
POLICY_METHODS = frozenset({"tool_policy_entail", "tool_policy_OR"})
SIGNATURE_FIELDS = frozenset({"asserted_condition", "asserted_rationale",
                              "induced_tool_preference", "scope_limitations"})
INVALID_EXTRACTION = frozenset({"blank_output", "output_too_large", "duplicate_key",
                               "malformed_json", "not_object", "schema_mismatch", "invalid_fields"})
STATUSES = frozenset({"selected", "abstained", "parse_failure", "selection_failure"})
TIMING_FIELDS = frozenset({"extraction_s", "filter_s", "selection_s", "total_s"})


class RecordError(ValueError):
    """The reported record does not match its supplied frozen inputs."""


def _require(test: bool, message: str) -> None:
    if not test:
        raise RecordError(message)


def _text(value: Any, name: str, *, blank: bool = False) -> str:
    _require(isinstance(value, str) and (blank or bool(value.strip())), f"{name} must be a string" + ("" if blank else " and nonblank"))
    return value


def _json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise RecordError("record must contain finite JSON data") from exc


def canonical_sha256(value: Any) -> str:
    return text_sha256(_json(value))


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mapping(value: Any, name: str, *, nonempty: bool = True) -> dict:
    _require(isinstance(value, Mapping) and (not nonempty or bool(value)), f"{name} must be an object")
    _require(all(isinstance(k, str) for k in value), f"{name} keys must be strings")
    _json(value)
    return copy.deepcopy(dict(value))


def _seal(body: dict, key: str) -> dict:
    return {**body, key: canonical_sha256(body)}


def _unseal(record: Mapping[str, Any], key: str, schema: str) -> dict:
    obj = _mapping(record, "record")
    _require(obj.get("schema") == schema, "unsupported record schema")
    digest = obj.pop(key, None)
    _require(digest == canonical_sha256(obj), f"{key} mismatch")
    return obj


def create_run_manifest(*, plan: Mapping[str, Any], config: Mapping[str, Any],
                        method: str, capture_control: str,
                        model_config: Mapping[str, Any], parser_identity: Mapping[str, Any],
                        evidence_scope: str = "synthetic_fixture") -> dict:
    """Pin one declared method/control and all configurations, not execution.

    The plan is preparation metadata. A valid manifest is not permission to
    start inference, an execution freeze, or native-harness parity evidence.
    """
    plan = _mapping(plan, "plan")
    config = _mapping(config, "config")
    model_config = _mapping(model_config, "model_config")
    parser_identity = _mapping(parser_identity, "parser_identity")
    for key in ("name", "revision"):
        _text(parser_identity.get(key), "parser_identity." + key)
    _text(method, "method")
    _text(capture_control, "capture_control")
    for key in ("candidate_methods", "capture_controls"):
        values = plan.get(key)
        _require(isinstance(values, list) and bool(values) and
                 all(isinstance(v, str) and bool(v.strip()) for v in values) and
                 len(set(values)) == len(values), f"plan.{key} must be a unique nonblank string list")
    _require(method in plan.get("candidate_methods", []), "method is not declared in plan")
    _require(capture_control in plan.get("capture_controls", []), "capture control is not declared in plan")
    _text(evidence_scope, "evidence_scope")
    _require(evidence_scope in {"synthetic_fixture", "reported_native", "reported_author_validated_local_port"}, "unknown evidence scope")
    return _seal({"schema": MANIFEST_SCHEMA, "plan_sha256": canonical_sha256(plan),
                  "config_sha256": canonical_sha256(config), "method": method,
                  "capture_control": capture_control, "model_config": model_config,
                  "model_config_sha256": canonical_sha256(model_config),
                  "parser_identity": parser_identity, "parser_identity_sha256": canonical_sha256(parser_identity),
                  "evidence_scope": evidence_scope, "execution_verified": False,
                  "native_efficacy_established": False, "warning": WARNING}, "manifest_sha256")


def validate_run_manifest(manifest: Mapping[str, Any], *, plan: Mapping[str, Any],
                          config: Mapping[str, Any]) -> dict:
    """Rebuild against the expected plan/config; stale changes are rejected."""
    body = _unseal(manifest, "manifest_sha256", MANIFEST_SCHEMA)
    expected = create_run_manifest(plan=plan, config=config, method=body.get("method"),
        capture_control=body.get("capture_control"), model_config=body.get("model_config"),
        parser_identity=body.get("parser_identity"), evidence_scope=body.get("evidence_scope"))
    _require(dict(manifest) == expected, "manifest differs from expected plan/config or binding fields")
    return copy.deepcopy(expected)


def _capture_binding(capture: Mapping[str, Any]) -> dict:
    capture = _mapping(capture, "capture")
    result = {"capture_id": _text(capture.get("capture_id"), "capture_id")}
    for stage in ("raw", "stored"):
        text = _text(capture.get(stage + "_memory"), "capture." + stage + "_memory")
        digest = text_sha256(text)
        _require(capture.get(stage + "_sha256") == digest, f"capture {stage} hash mismatch")
        result[stage + "_sha256"] = digest
    return result


def _selection_projection(case: Mapping[str, Any], kept_indices: Sequence[int]) -> tuple[dict, list[str], list[int]]:
    """Whitelist model-visible content; all scorer/identity fields stay out."""
    _text(case.get("case_id"), "case_id")
    state = _text(case.get("state"), "case.state")
    tools = case.get("tools")
    memories = case.get("memories")
    _require(isinstance(tools, list) and bool(tools), "case.tools must be a nonempty list")
    names = []
    for tool in tools:
        _require(isinstance(tool, Mapping) and set(tool) <= {"name", "description", "parameters"}, "tool has undeclared/scorer fields")
        names.append(_text(tool.get("name"), "tool.name"))
        _text(tool.get("description", ""), "tool.description", blank=True)
        _mapping(tool.get("parameters", {}), "tool.parameters", nonempty=False)
    _require(len(set(names)) == len(names), "duplicate tool name")
    _require(isinstance(memories, list), "case.memories must be a list")
    texts = []
    for memory in memories:
        _require(isinstance(memory, Mapping), "memory must be an object")
        text = _text(memory.get("text"), "memory.text")
        _require(memory.get("stored_sha256") == text_sha256(text), "stored memory hash mismatch")
        texts.append(text)
    _require(isinstance(kept_indices, (list, tuple)), "kept_indices must be an explicit list or tuple")
    indices = list(kept_indices)
    _require(all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(texts) for i in indices), "kept index is out of range or not an integer")
    _require(indices == sorted(set(indices)), "kept indices must preserve original order without duplicates")
    return {"state": state, "tools": copy.deepcopy(tools),
            "memories": [{"text": texts[i]} for i in indices]}, texts, indices


def build_case_request(manifest: Mapping[str, Any], case: Mapping[str, Any],
                       capture: Mapping[str, Any], *, kept_indices: Sequence[int],
                       extraction_status: str, signature: Mapping[str, Any] | None = None,
                       extraction_raw_output: str | None = None,
                       signature_state: str = "active") -> dict:
    """Bind one post-filter input while keeping private metadata out of it.

    The source case should also pass the native fixture validator. This
    projection does not replace native prompt review. It permits deletion
    only, never hidden refill/reordering, and binds rather than validates the
    scientific filter scores/semantics that produced the kept indices.
    """
    body = _unseal(manifest, "manifest_sha256", MANIFEST_SCHEMA)
    case = _mapping(case, "case")
    model_input, texts, indices = _selection_projection(case, kept_indices)
    binding = _capture_binding(capture)
    _text(extraction_status, "extraction_status")
    _text(signature_state, "signature_state")
    _require(extraction_status in INVALID_EXTRACTION | {"valid", "not_requested"}, "unknown extraction status")
    _require(signature_state in {"active", "revoked", "expired", "absent"}, "unknown signature state")
    if signature is not None:
        signature = _mapping(signature, "signature")
        _require(set(signature) == SIGNATURE_FIELDS, "signature needs exactly four capture-derived fields")
        for key, value in signature.items():
            _text(value, "signature." + key)
    if extraction_raw_output is not None:
        _text(extraction_raw_output, "extraction_raw_output", blank=True)
    all_indices = list(range(len(texts)))
    if body["method"] == "none":
        _require(indices == all_indices and signature is None, "none baseline must retain all memories without a signature")
        _require(extraction_status == "not_requested", "none baseline does not extract a signature")
    if body["method"] in POLICY_METHODS:
        if extraction_status == "valid" and signature_state == "active":
            _require(signature is not None, "active valid policy extraction needs its signature")
        else:
            _require(indices == all_indices, "inactive/invalid policy extraction must pass all memories through")
        _require(extraction_status != "not_requested", "policy method needs a recorded extraction outcome")
    if extraction_status in INVALID_EXTRACTION:
        _require(signature is None, "invalid extraction cannot carry a valid signature")
        _require(extraction_raw_output is not None, "invalid extraction needs exact raw output evidence")
    return _seal({"schema": REQUEST_SCHEMA, "manifest_sha256": manifest["manifest_sha256"],
        "case_id": case["case_id"], "case_sha256": canonical_sha256(case),
        "capture": binding, "method": body["method"], "capture_control": body["capture_control"],
        "kept_indices": indices, "input_memory_hashes": list(map(text_sha256, texts)),
        "post_filter_memory_hashes": [text_sha256(texts[i]) for i in indices],
        "extraction_status": extraction_status, "signature_state": signature_state,
        "signature": signature, "extraction_raw_output": extraction_raw_output,
        "signature_sha256": canonical_sha256(signature) if signature is not None else None,
        "extraction_raw_output_sha256": text_sha256(extraction_raw_output) if extraction_raw_output is not None else None,
        "model_input": model_input, "model_input_sha256": canonical_sha256(model_input),
        "input_contract": "whitelisted_selection_projection_not_native_prompt_parity",
        "warning": WARNING}, "request_sha256")


def _timings(timings: Mapping[str, Any]) -> dict[str, float]:
    _require(isinstance(timings, Mapping) and set(timings) == TIMING_FIELDS,
             "timings need extraction_s, filter_s, selection_s and total_s")
    _require(all(isinstance(v, Real) and not isinstance(v, bool) and math.isfinite(v) and v >= 0 for v in timings.values()),
             "timings must be finite nonnegative seconds")
    values = {key: float(value) for key, value in timings.items()}
    _require(values["total_s"] + 1e-9 >= max(values[k] for k in TIMING_FIELDS - {"total_s"}), "total time is shorter than a component")
    return values


def record_observation(manifest: Mapping[str, Any], request: Mapping[str, Any], *,
                       status: str, selected_tool: str | None, raw_response: str | None,
                       timings: Mapping[str, Any], error: str | None = None,
                       execution_kind: str = "inert_callback") -> dict:
    """Keep raw output and explicit failures; never declare empirical success."""
    run = _unseal(manifest, "manifest_sha256", MANIFEST_SCHEMA)
    req = _unseal(request, "request_sha256", REQUEST_SCHEMA)
    _require(req.get("manifest_sha256") == manifest["manifest_sha256"], "request belongs to another run")
    _text(status, "status")
    _text(execution_kind, "execution_kind")
    _require(status in STATUSES, "unknown observation status")
    _require(execution_kind in {"inert_callback", "reported_native", "reported_local_port"}, "unknown execution kind")
    _require(execution_kind != "inert_callback" or run["evidence_scope"] == "synthetic_fixture", "inert callbacks must remain synthetic software evidence")
    _require(execution_kind != "reported_native" or run["evidence_scope"] == "reported_native", "synthetic/local-port records cannot be relabelled as native execution")
    _require(execution_kind != "reported_local_port" or run["evidence_scope"] == "reported_author_validated_local_port", "synthetic/native records cannot be relabelled as local-port execution")
    if status == "selected":
        _require(isinstance(selected_tool, str) and selected_tool in {t["name"] for t in req["model_input"]["tools"]}, "selected tool absent from catalog")
    else:
        _require(selected_tool is None, "non-selection result must not report a tool")
    if status == "selection_failure":
        _require(raw_response is None, "selection failure must not invent a decoder response")
    else:
        _text(raw_response, "raw_response", blank=True)
    if status in {"parse_failure", "selection_failure"}:
        _text(error, "failure.error")
    else:
        _require(error is None, "successful parsing must not carry a failure error")
    return _seal({"schema": OBSERVATION_SCHEMA, "manifest_sha256": manifest["manifest_sha256"],
        "request_sha256": request["request_sha256"], "case_id": req["case_id"],
        "method": run["method"], "capture_control": run["capture_control"],
        "model_input_sha256": req["model_input_sha256"],
        "post_filter_memory_hashes": req["post_filter_memory_hashes"],
        "extraction_status": req["extraction_status"], "signature_state": req["signature_state"],
        "parser_identity_sha256": run["parser_identity_sha256"],
        "model_config_sha256": run["model_config_sha256"],
        "status": status, "selected_tool": selected_tool, "raw_response": raw_response,
        "raw_response_sha256": text_sha256(raw_response) if raw_response is not None else None,
        "timings": _timings(timings), "error": error, "execution_kind": execution_kind,
        "execution_verified": False, "native_efficacy_established": False,
        "warning": WARNING}, "observation_sha256")


def validate_observation(manifest: Mapping[str, Any], request: Mapping[str, Any],
                         observation: Mapping[str, Any], *, case: Mapping[str, Any],
                         capture: Mapping[str, Any],
                         parser_callback: Callable[[str], Mapping[str, Any]] | None = None) -> dict:
    """Validate against expected request and current source case/capture.

    The caller must separately validate the run against its expected plan and
    config. Re-signing fabricated data cannot authenticate execution; this
    checks consistency with the caller's supplied expected records only. An
    optional parser callback replays parsing of exact raw output; supplying
    the reviewed parser matching its declared identity remains the caller's
    responsibility. Without it, parsed choices are reported, not reverified.
    """
    req = _unseal(request, "request_sha256", REQUEST_SCHEMA)
    obs = _unseal(observation, "observation_sha256", OBSERVATION_SCHEMA)
    _require(req["case_sha256"] == canonical_sha256(case), "case changed or different case supplied")
    _require(req["capture"] == _capture_binding(capture), "capture changed or different capture supplied")
    model_input, texts, indices = _selection_projection(case, req["kept_indices"])
    _require(req["model_input"] == model_input and req["model_input_sha256"] == canonical_sha256(model_input), "runtime model input does not match expected case/context")
    _require(req["input_memory_hashes"] == list(map(text_sha256, texts)) and
             req["post_filter_memory_hashes"] == [text_sha256(texts[i]) for i in indices], "post-filter memory hashes mismatch")
    expected_request = build_case_request(manifest, case, capture,
        kept_indices=req["kept_indices"], extraction_status=req["extraction_status"],
        signature=req.get("signature"), extraction_raw_output=req.get("extraction_raw_output"),
        signature_state=req["signature_state"])
    _require(dict(request) == expected_request, "request differs from expected source/run/extraction bindings")
    expected = record_observation(manifest, request, status=obs.get("status"), selected_tool=obs.get("selected_tool"),
        raw_response=obs.get("raw_response"), timings=obs.get("timings"), error=obs.get("error"),
        execution_kind=obs.get("execution_kind"))
    _require(dict(observation) == expected, "observation differs from expected request/run/result bindings")
    if parser_callback is not None and obs["status"] != "selection_failure":
        status, selected, _ = _parse_output(obs["raw_response"], req["model_input"]["tools"], parser_callback)
        _require(status == obs["status"] and selected == obs["selected_tool"], "reported result differs from raw-response parser replay")
    return copy.deepcopy(expected)


def _parse_output(raw: str, tools: list[dict], parser: Callable[[str], Mapping[str, Any]]) -> tuple[str, str | None, str | None]:
    try:
        parsed = _mapping(parser(raw), "parser output")
        _require(set(parsed) == {"status", "selected_tool"}, "parser output needs status and selected_tool only")
        status, selected = parsed["status"], parsed["selected_tool"]
        _require(status in {"selected", "abstained"}, "parser did not return a selection or abstention")
        if status == "selected":
            _require(isinstance(selected, str) and selected in {t["name"] for t in tools}, "parsed tool absent from catalog")
        else:
            _require(selected is None, "abstention must not select a tool")
        return status, selected, None
    except Exception as exc:
        return "parse_failure", None, f"{type(exc).__name__}: {exc}"


def execute_inert_case(manifest: Mapping[str, Any], request: Mapping[str, Any],
                       selection_callback: Callable[[dict], str],
                       parser_callback: Callable[[str], Mapping[str, Any]]) -> dict:
    """Exercise the software boundary using caller-supplied inert functions.

    No model, tool or network client is imported or invoked by this module.
    Callers must supply inert callbacks; a hash cannot verify that promise.
    This helper refuses any non-synthetic manifest and records failures once,
    without retries or repaired outputs. Extraction/filter timing is not
    measured here (zero); only this projection's selection/parse wall time is.
    """
    run = _unseal(manifest, "manifest_sha256", MANIFEST_SCHEMA)
    req = _unseal(request, "request_sha256", REQUEST_SCHEMA)
    _require(run["evidence_scope"] == "synthetic_fixture", "inert helper requires synthetic scope")
    _require(req["manifest_sha256"] == manifest["manifest_sha256"], "request belongs to another run")
    start = time.perf_counter()
    raw = None
    try:
        raw = selection_callback(copy.deepcopy(req["model_input"]))
        _text(raw, "callback raw response", blank=True)
    except Exception as exc:
        status, selected, error = "selection_failure", None, f"{type(exc).__name__}: {exc}"
        raw = None
    else:
        status, selected, error = _parse_output(raw, req["model_input"]["tools"], parser_callback)
    elapsed = time.perf_counter() - start
    return record_observation(manifest, request, status=status, selected_tool=selected,
        raw_response=raw, error=error,
        timings={"extraction_s": 0., "filter_s": 0., "selection_s": elapsed, "total_s": elapsed})
