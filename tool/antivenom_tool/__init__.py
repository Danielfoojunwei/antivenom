"""AntiVenom: turn one caught poisoned record into protection for every agent.

    from antivenom_tool import Signature, make_signature, Defender, OpenAICompatibleLLM

    sig = make_signature(caught_record_text, OpenAICompatibleLLM("openai/gpt-4o-mini"))
    report = Defender([sig]).check(retrieved_passages, query)
    use(report.kept)
"""
__version__ = "0.1.0"

from .backends import (CallableLLM, CrossEncoderEntailment, LLMJudgeEntailment,  # noqa: E402
                       OpenAICompatibleLLM)
from .defender import Defender, PassageVerdict, Report  # noqa: E402
from .registry import SignatureRegistry, SignatureRejected, sign, verify  # noqa: E402
from .signature import ExtractionError, Signature, make_signature  # noqa: E402
from .adapters import GuardedRetriever, filter_nodes, guard_retriever, text_of  # noqa: E402

__all__ = ["Signature", "make_signature", "ExtractionError", "Defender", "Report", "PassageVerdict",
           "SignatureRegistry", "SignatureRejected", "sign", "verify", "OpenAICompatibleLLM", "CallableLLM",
           "CrossEncoderEntailment", "LLMJudgeEntailment", "guard_retriever", "GuardedRetriever", "filter_nodes", "text_of"]
