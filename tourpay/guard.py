"""Deterministic guard for money-moving chat actions (refund, capture). No model is involved here.

A message that merely MENTIONS "refund" is not an instruction to refund. `speech_act` looks at the clause that holds the
keyword (or the whole message when a model supplied the intent) and answers one of:
  "negated"  - "don't refund", "不要退款", "đừng hoàn tiền", "no refund, thanks", "cancel the refund"
  "question" - "what is your refund policy?", "能退款吗", "if I refund ...", "chính sách hoàn tiền thế nào"
  "command"  - everything else ("refund", "please refund order X", "请退款", "hoàn tiền đơn này")
Fail-safe direction: when in doubt the answer is NOT "command". Even a "command" never moves money by itself: refunds need
a second, explicit confirmation turn (see Agent), so a wrong "command" costs one extra summary message, not a refund.
"""
import re

_CLAUSE = re.compile(r"[^,;.!?。，；！？、\n]+[,;.!?。，；！？、\n]*")
_SPLIT_WORDS = re.compile(r"\b(?:but|however|then)\b|但是|但|不过|可是|然后|rồi|nhưng", re.I)

NEG = re.compile(
    r"\b(?:don'?t|do\s+not|dont|doesn'?t|does\s+not|didn'?t|did\s+not|won'?t|will\s+not|can'?t|cannot|shouldn'?t|never|never\s*mind|nevermind|"
    r"no|nope|not|without|cancel(?:l?ed)?|stop|abort|skip|avoid|hold\s+(?:off|on)|instead\s+of|khong|dung)\b"
    r"|不|别|没|未|勿|无需|取消|算了|khỏi|đừng|không|chưa|hủy|thôi", re.I)
# policy / hypothetical wording: always informational, even with "please"
HYPO = re.compile(
    r"\b(?:if|whether|suppose|supposing|in\s+case|policy|policies|eligible|eligibility|possible|allowed|how\s+long|how\s+much|how\s+do|how\s+can|how\s+to)\b"
    r"|政策|规定|条件|规则|如果|假如|假设|万一|要是|多久|如何|怎么|怎样|是否|chính sách|quy định|điều kiện|nếu|giả sử|bao lâu|làm sao|làm thế nào|liệu", re.I)
# plain questions
QUES = re.compile(
    r"\?|？|^\s*(?:what|what'?s|whats|when|why|where|which|who|is|are|was|were|do|does|did|can|could|would|should|will|may|might)\b"
    r"|吗|嘛|么|呢|能否|可否|能不能|可不可以|会不会|有没有|什么|何时|là gì|thế nào|khi nào|được không|có thể.*không|có.*không", re.I)
# an explicit request wording that turns a "can you ...?" question into a request (still only a proposal for refunds)
POLITE = re.compile(r"\b(?:can|could|would|will)\s+you\b|\bplease\b|请(?!问)|麻烦|帮我|giúp|vui lòng|làm ơn", re.I)


def clauses(text):
    out = []
    for c in _CLAUSE.findall(text):
        out.extend(p for p in _SPLIT_WORDS.split(c) if p and p.strip())
    return out or [text]


def speech_act(text, keyword_rx=None):
    """Classify how `text` relates to the action. keyword_rx selects the clause(s) to judge; without a match
    (e.g. the model, not our rules, supplied the intent) every clause counts, which is stricter."""
    cs = clauses(text)
    if keyword_rx is not None:
        hit = [c for c in cs if keyword_rx.search(c)]
        cs = hit or cs
    acts = []
    for c in cs:
        if NEG.search(c): acts.append("negated")
        elif HYPO.search(c): acts.append("question")
        elif QUES.search(c) and not POLITE.search(c): acts.append("question")
        else: acts.append("command")
    for a in ("negated", "question"):          # any doubtful clause wins over a plain command
        if a in acts: return a
    return "command"


# A confirmation must be (almost) nothing but a yes. Anything else - a new request, another order, a question - is not one.
CONFIRM = {
    "en": re.compile(r"(?:yes|y|yeah|yep|ok|okay|sure|confirm(?:ed)?|go\s+ahead|proceed|do\s+it)(?:[\s,]+(?:please|refund(?:\s+it)?|confirm(?:\s+refund)?|it|now))*", re.I),
    "zh": re.compile(r"(?:是的?|好的?|对|同意|确认|可以)(?:[\s，,]*(?:退款|确认退款|确认|请|吧))*", re.I),
    "vi": re.compile(r"(?:vâng|dạ|ừ|ok|đồng ý|xác nhận|có)(?:[\s,]+(?:hoàn tiền|xác nhận(?:\s+hoàn tiền)?|ạ|nhé|đi))*", re.I),
}

def is_confirmation(text_without_order_id):
    s = re.sub(r"[\s.!。！]+$", "", text_without_order_id.strip())
    return bool(s) and any(rx.fullmatch(s) for rx in CONFIRM.values())
