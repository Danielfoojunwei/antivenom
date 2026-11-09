"""Run an MLX Qwen2-style model layer by layer with a custom attention mask.

The mask is additive and is applied in every layer. Zero everywhere except the
causal part reproduces the model's normal forward pass.
"""
import mlx.core as mx
import numpy as np


def causal_mask(n: int) -> mx.array:
    upper = mx.triu(mx.ones((n, n)), k=1)
    return upper * -1e9


def token_spans(hf_tok, text: str, pieces: list[str]) -> tuple[list[int], list[tuple[int, int]]]:
    """Tokenise ``text``; return ids and the token range covering each piece.

    Pieces are located in order by character position, then mapped to tokens
    through the tokenizer's offset mapping.
    """
    enc = hf_tok(text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = enc["offset_mapping"]
    spans, cursor = [], 0
    for p in pieces:
        start = text.index(p, cursor)
        end = start + len(p)
        cursor = end
        toks = [i for i, (a, b) in enumerate(offsets) if a < end and b > start]
        spans.append((toks[0], toks[-1] + 1))
    return enc["input_ids"], spans


def _run_layers(model, h, mask, cache):
    inner = model.model
    m = mask.astype(h.dtype)[None, None]
    for layer, c in zip(inner.layers, cache):
        h = layer(h, m, c)
    h = inner.norm(h[:, -1:, :])
    if getattr(model.args, "tie_word_embeddings", False):
        return inner.embed_tokens.as_linear(h)[0, -1]
    return model.lm_head(h)[0, -1]


def generate_masked(model, tokenizer, ids: list[int], blocked: list[tuple[int, int]],
                    strength: float, from_row: int, max_tokens: int = 48) -> str:
    """Greedy decoding where every position at or after ``from_row`` gets
    ``strength`` added to its attention logits toward the ``blocked`` spans.
    With ``blocked`` empty this is ordinary greedy decoding."""
    from mlx_lm.models.cache import make_prompt_cache

    cache = make_prompt_cache(model)
    n = len(ids)
    mask = np.array(causal_mask(n))
    for a, b in blocked:
        mask[from_row:, a:b] += strength
    logits = _run_layers(model, model.model.embed_tokens(mx.array([ids])), mx.array(mask), cache)
    out = []
    eos = set(tokenizer.eos_token_ids)
    for _ in range(max_tokens):
        nxt = int(mx.argmax(logits).item())
        if nxt in eos:
            break
        out.append(nxt)
        row = np.zeros((1, n + len(out)), dtype=np.float32)
        for a, b in blocked:
            row[0, a:b] += strength
        logits = _run_layers(model, model.model.embed_tokens(mx.array([[nxt]])), mx.array(row), cache)
    return tokenizer.decode(out)


def attention_rows(model, ids: list[int], rows: list[int], layers: list[int]) -> dict:
    """Attention probabilities from the given query rows, per chosen layer.

    Returns {layer: array (heads, len(rows), n)}. Recomputes q and k from the
    layer's own projections and rotary embedding; values are not needed.
    """
    inner = model.model
    n = len(ids)
    h = inner.embed_tokens(mx.array([ids]))
    mask = causal_mask(n).astype(h.dtype)[None, None]
    out = {}
    for li, layer in enumerate(inner.layers):
        if li in layers:
            attn = layer.self_attn
            x = layer.input_layernorm(h)
            q = attn.q_proj(x).reshape(1, n, attn.n_heads, -1).transpose(0, 2, 1, 3)
            k = attn.k_proj(x).reshape(1, n, attn.n_kv_heads, -1).transpose(0, 2, 1, 3)
            q, k = attn.rope(q), attn.rope(k)
            k = mx.repeat(k, attn.n_heads // attn.n_kv_heads, axis=1).astype(mx.float32)
            sel = mx.array(rows)
            qs = q[:, :, sel, :].astype(mx.float32)  # float32: late layers overflow in fp16
            scores = (qs @ k.transpose(0, 1, 3, 2)) * attn.scale + mask[:, :, sel, :].astype(mx.float32)
            out[li] = np.array(mx.softmax(scores, axis=-1)[0])
        h = layer(h, mask, None)
        if li >= max(layers):
            break
    return out


def forward_logits(model, ids: list[int], mask: mx.array, only_layers=None) -> mx.array:
    """Return logits of shape (n, vocab) using ``mask`` of shape (n, n).

    If ``only_layers`` is given, ``mask`` is used in those layers and the plain
    causal mask everywhere else (to localise where a blockade acts)."""
    inner = model.model
    h = inner.embed_tokens(mx.array([ids]))
    m = mask.astype(h.dtype)[None, None]
    plain = causal_mask(len(ids)).astype(h.dtype)[None, None]
    for li, layer in enumerate(inner.layers):
        h = layer(h, m if only_layers is None or li in only_layers else plain, None)
    h = inner.norm(h)
    if getattr(model.args, "tie_word_embeddings", False):
        logits = inner.embed_tokens.as_linear(h)
    else:
        logits = model.lm_head(h)
    return logits[0]
