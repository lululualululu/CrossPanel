"""Answer extraction is independent of gold. Strict schema and answer accuracy are separate."""

import json
import re

VERSION = "choice-v2"


class Obj(dict):
    def __init__(self, pairs):
        super().__init__(pairs)
        self.duplicate = len(pairs) != len(self)
        self.pairs = pairs


DEC = json.JSONDecoder(object_pairs_hook=Obj)


def valid_choice(x):
    return isinstance(x, str) and x in ("A", "B", "C", "D")


def score_text(text):
    s = text.strip()
    whole = None
    try:
        whole = DEC.decode(s)
    except (ValueError, TypeError):
        pass
    strict = (
        isinstance(whole, Obj)
        and not whole.duplicate
        and set(whole) == {"explanation", "choice"}
        and isinstance(whole.get("explanation"), str)
        and valid_choice(whole.get("choice"))
    )
    objects = []
    i = 0
    while i < len(s):
        if s[i] == "{":
            try:
                obj, end = DEC.raw_decode(s, i)
                if isinstance(obj, Obj) and "choice" in obj:
                    objects.append(obj)
                i = end
                continue
            except ValueError:
                pass
        i += 1
    choices = []
    for obj in objects:
        choices.extend(v for k, v in obj.pairs if k == "choice" and valid_choice(v))
    # Explicit malformed choice fields are recoverable; never search arbitrary A-D prose.
    if not choices:
        choices = re.findall(
            r"""(?im)^\s*["']?choice["']?\s*:\s*["']?([ABCD])["']?\s*[,}.]?\s*$""", s
        )
    if not choices:
        # Recover an explicit terminal field even when explanation has illegal JSON escapes.
        choices = re.findall(
            r"""["']choice["']\s*:\s*["']([ABCD])["']\s*}\s*(?:```)?\s*$""", s
        )
    method = "json" if objects else "explicit_choice_field"
    if not choices:
        # A standalone final letter, or final letter with option wording, is an explicit selection.
        last = s.splitlines()[-1].strip() if s else ""
        m = re.fullmatch(r"(?:\*\*)?([ABCD])(?:\*\*)?(?:[.)](?:\s+.+)?)?", last)
        if m:
            choices = [m.group(1)]
            method = "final_choice_line"
    unique = set(choices)
    if len(unique) > 1:
        return {
            "choice": None,
            "format_valid": False,
            "parse_method": "conflicting_choices",
            "parser_version": VERSION,
        }
    return {
        "choice": next(iter(unique)) if unique else None,
        "format_valid": bool(strict),
        "parse_method": method if unique else "missing_choice",
        "parser_version": VERSION,
    }


RELAXED_VERSION = "internvl-explicit-answer-v1"


def score_internvl(text):
    """Recover explicit declarations only; preserve strict schema and conflicts."""
    d = score_text(text)
    d["parser_version"] = VERSION + "+" + RELAXED_VERSION
    if d["choice"] is not None or d["parse_method"] == "conflicting_choices":
        return d
    vals = re.findall(
        r"""(?i:\b(?:the\s+)?(?:final\s+|correct\s+)?answer\s*(?:is\s*:?|:)\s*)(?:\*\*|["'])?([A-D])\b""",
        text,
    )
    vals += re.findall(r"\\boxed\s*\{\s*([A-D])\s*\}", text)
    vals += re.findall(r"""["']choice["']\s*:\s*["']([A-D])["']""", text)
    if len(set(vals)) == 1:
        d.update(choice=vals[0], parse_method="internvl_explicit_answer")
    elif vals:
        d.update(parse_method="conflicting_choices")
    return d


def extract_uniform(text, finish_reason="stop"):
    """Gold-blind, model-independent. Truncated prose needs a final declaration.
    Complete JSON/choice fields remain valid even when the overall generation hit its cap.
    Never infer a choice from arbitrary A-D mentions, intermediate speculation, or a gold answer.
    """
    d = score_text(text)
    relaxed = score_internvl(text)
    if d["choice"] is None and d["parse_method"] != "conflicting_choices":
        if finish_reason != "length":
            d = relaxed
            other = re.findall(
                r"(?i:option|choice)\s+\*{0,2}([A-D])\*{0,2}\s+(?i:(?:is\s+)?(?:the\s+)?correct\s+(?:answer|choice))",
                text,
            )
            vals = set(other + ([d["choice"]] if d["choice"] is not None else []))
            if len(vals) > 1:
                d.update(choice=None, parse_method="conflicting_choices")
            elif len(vals) == 1 and d["parse_method"] != "conflicting_choices":
                d.update(choice=next(iter(vals)), parse_method="explicit_answer")
        else:
            # A final declaration at the end, or directly before an unfinished output JSON.
            tail = text.strip().split("\n\n")[-1]
            before_json = re.split(r'\{\s*["\']explanation["\']\s*:', text)[0].rstrip()
            if before_json != text.rstrip() and before_json:
                tail = before_json.split("\n\n")[-1]
            explicit_final = bool(
                re.search(r"(?i)final\s+(?:answer|decision)\s*(?::|is\b)", tail)
            )
            candidates = score_internvl(tail)
            if candidates["choice"] is None and explicit_final:
                vals = re.findall(
                    r"(?i:closest\s+option\s+is)\s*\*{0,2}([A-D])\b", tail
                )
                if len(set(vals)) == 1:
                    candidates.update(
                        choice=vals[0], parse_method="explicit_final_option"
                    )
            # A truncation before the answer finishes does not become a choice just because
            # an intermediate paragraph once mentioned an answer letter.
            reconsider = bool(
                re.search(
                    r"(?i)\b(?:but|wait|perhaps|maybe|however|assume|if)\b|\?", tail
                )
            )
            if explicit_final and not reconsider and candidates["choice"] is not None:
                d.update(
                    choice=candidates["choice"],
                    parse_method="explicit_final_before_truncation",
                )
            elif relaxed["choice"] is not None:
                d.update(
                    choice=None, parse_method="unfinished_prose_without_final_selection"
                )
    d["parser_version"] = "uniform-explicit-final-v2-20261116"
    if d["parse_method"] == "internvl_explicit_answer":
        d["parse_method"] = "explicit_answer"
    return d


FINAL_VERSION = "uniform-explicit-final-v3-case-20261117"


def score_uniform(text, finish_reason="stop"):
    original = extract_uniform(text, finish_reason)
    s = re.sub(
        r"""(["']choice["']\s*:\s*["'])([a-d])(["'])""",
        lambda m: m[1] + m[2].upper() + m[3],
        text,
    )
    s = re.sub(
        r"""(?im)^(\s*["']?choice["']?\s*:\s*["']?)([a-d])(["']?\s*[,}.]?\s*)$""",
        lambda m: m[1] + m[2].upper() + m[3],
        s,
    )
    lines = s.splitlines()
    if lines and re.fullmatch(r"\s*[a-d]\s*", lines[-1]):
        lines[-1] = lines[-1].upper()
        s = "\n".join(lines)
    d = extract_uniform(s, finish_reason)
    d["format_valid"] = original["format_valid"]
    d["parser_version"] = FINAL_VERSION
    d["case_normalized"] = s != text
    return d
