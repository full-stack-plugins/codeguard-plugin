"""用户提交意图与语言子集的纯策略，不读取宿主事件或执行门禁。"""
from __future__ import annotations

import re

TRIGGER_PATTERNS = ["commit", "push", "deploy", "提交", "发布", "部署"]
_TRIGGER_RE = re.compile(r"\b(?:commit|push|deploy)\b|提交|发布|部署", re.IGNORECASE)
_ACTION_INTENT_RE = re.compile(
    r"请帮我|帮我|请|马上|立刻|现在|下一步|继续|please|now|next|proceed|go ahead|"
    r"commit this|push this|deploy this",
    re.IGNORECASE,
)
QUESTION_MARKERS = ("？", "?", "么", "吗", "如何", "怎么", "有没有", "是不是", "什么是", "哪些")


def is_trigger(user_text: str) -> bool:
    """仅行动句触发软门禁；疑问句、陈述既往动作和词内子串不触发。"""
    if not user_text:
        return False
    parts = re.split(r"([。！!？?\n\r]+)", user_text)
    sentences = []
    for i in range(0, len(parts) - 1, 2):
        segment = (parts[i] + parts[i + 1]).strip()
        if segment:
            sentences.append(segment)
    tail = parts[-1].strip() if len(parts) % 2 == 1 else ""
    if tail:
        sentences.append(tail)
    trigger_sentences = [segment for segment in sentences if _TRIGGER_RE.search(segment)]
    if not trigger_sentences:
        return False
    non_question = [segment for segment in trigger_sentences
                    if not any(marker in segment for marker in QUESTION_MARKERS)]
    if not non_question:
        return False
    match = _TRIGGER_RE.search(non_question[0])
    if not match:
        return False
    leading = non_question[0].lstrip()[:match.start()].strip().lower()
    if leading in ("", "git", "to", "the", "a", "an", "帮我", "请", "请帮我"):
        return True
    return bool(_ACTION_INTENT_RE.search(user_text))


def detect_languages_in_text(user_text: str, language_ids: list[str]) -> list[str]:
    """用户明确提到语言时只选择对应注册项；无命中由调用方回退全量。"""
    if not user_text or not language_ids:
        return []
    text = user_text.lower()
    return [lang_id for lang_id in language_ids
            if re.search(rf"\b{re.escape(lang_id.lower())}\b", text)]


def intent_mode(user_text: str) -> str:
    """推送意图包含未推送提交；其余提交/发布意图按 commit 面观察。"""
    return "push" if re.search(r"\bpush\b|推送", user_text, re.IGNORECASE) else "commit"
