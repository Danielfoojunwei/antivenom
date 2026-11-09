"""Drop AntiVenom into an existing harness.

Nothing here imports a framework. Adapters use duck typing, so they work with
LangChain, LlamaIndex, Haystack, DSPy or a hand-written loop:

  * ``guard_retriever(fn, defender)``: wrap any ``fn(query, k) -> list[str | doc]``.
  * ``GuardedRetriever(retriever, defender)``: wrap an object with ``invoke(query)``
    or ``get_relevant_documents(query)`` returning documents with ``page_content``
    (LangChain style). Returns the same document objects, minus flagged ones.
  * ``filter_nodes(nodes, defender, query)``: LlamaIndex-style nodes with
    ``get_content()`` or ``.node.get_content()``; use inside a node postprocessor.
  * ``text_of(item)``: how any of the above is turned into text.

Registry-backed defenders pick up new signatures on every call via ``sync``.
"""
from __future__ import annotations

from typing import Any, Callable, Sequence

from .defender import Defender, Report
from .registry import SignatureRegistry


def text_of(item: Any) -> str:
    if isinstance(item, str):
        return item
    for attr in ("page_content", "text", "content"):
        v = getattr(item, attr, None)
        if isinstance(v, str):
            return v
    for obj in (item, getattr(item, "node", None)):
        f = getattr(obj, "get_content", None)
        if callable(f):
            return f()
    if isinstance(item, dict):
        for k in ("page_content", "text", "content"):
            if isinstance(item.get(k), str):
                return item[k]
    return str(item)


def sync(defender: Defender, registry: SignatureRegistry | None) -> None:
    """Make the defender's signatures match the registry's active ones."""
    if registry is None:
        return
    active = {s.id: s for s in registry.refresh()}
    defender.signatures = active


def _filter_items(items: Sequence[Any], defender: Defender, query: str) -> tuple[list[Any], Report]:
    texts = [text_of(x) for x in items]
    rep = defender.check(texts, query)
    flagged = {v.index for v in rep.verdicts if v.flagged}
    return [x for i, x in enumerate(items) if i not in flagged], rep


def guard_retriever(fn: Callable[..., Sequence[Any]], defender: Defender, *,
                    registry: SignatureRegistry | None = None, overfetch: int = 5,
                    on_report: Callable[[Report], None] | None = None):
    """Wrap ``fn(query, k)``. Fetches ``k + overfetch`` results so removed
    passages are refilled with the next-ranked ones, then returns ``k`` items."""
    def wrapped(query: str, k: int = 10, **kw):
        sync(defender, registry)
        items = list(fn(query, k + overfetch, **kw))
        head, tail = items[:k], items[k:]
        kept, rep = _filter_items(head, defender, query)
        if len(kept) < k and tail:
            more, _ = _filter_items(tail, defender, query)
            kept += more[: k - len(kept)]
        if on_report:
            on_report(rep)
        return kept[:k]
    return wrapped


class GuardedRetriever:
    """Wraps a LangChain-style retriever (``invoke`` / ``get_relevant_documents``)."""

    def __init__(self, retriever: Any, defender: Defender, registry: SignatureRegistry | None = None):
        self.retriever, self.defender, self.registry = retriever, defender, registry
        self.last_report: Report | None = None

    def _raw(self, query: str):
        if hasattr(self.retriever, "invoke"):
            return self.retriever.invoke(query)
        return self.retriever.get_relevant_documents(query)

    def invoke(self, query: str, *a, **kw):
        sync(self.defender, self.registry)
        kept, self.last_report = _filter_items(list(self._raw(query)), self.defender, query)
        return kept

    get_relevant_documents = invoke

    def __getattr__(self, name):
        return getattr(self.retriever, name)


def filter_nodes(nodes: Sequence[Any], defender: Defender, query: str = "",
                 registry: SignatureRegistry | None = None) -> list[Any]:
    """LlamaIndex-style: return the nodes that pass the check."""
    sync(defender, registry)
    kept, _ = _filter_items(list(nodes), defender, query)
    return kept
