"""Run and score the public CrossPanel samples using the Python standard library."""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .answer_parser import score_uniform

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def indexed_rows(path):
    rows = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = row["id"]
        if not isinstance(key, str) or not key or key in rows:
            raise ValueError(f"{path}:{number}: duplicate or invalid id {key!r}")
        rows[key] = row
    return rows


def infer(args, question):
    image = (SAMPLES / question["image"]).read_bytes()
    data_url = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
    content = [
        {"type": "image_url", "image_url": {"url": data_url}},
        {"type": "text", "text": question["prompt"]},
    ]
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": args.max_tokens,
    }
    if args.reasoning_effort:
        body["reasoning_effort"] = args.reasoning_effort
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("CROSSPANEL_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = Request(
        args.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers=headers,
    )
    try:
        with urlopen(request, timeout=args.timeout) as response:
            choice = json.load(response)["choices"][0]
    except HTTPError as exc:
        raise ValueError(
            f"{question['id']}: endpoint returned HTTP {exc.code}: "
            f"{exc.read(500).decode(errors='replace')}"
        ) from exc
    text = choice["message"]["content"]
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise TypeError(f"{question['id']}: expected a text response")
    return {
        "id": question["id"],
        "model": args.model,
        "text": text,
        "finish_reason": choice.get("finish_reason") or "stop",
    }


def predict(args, questions):
    if args.max_tokens < 1 or args.timeout < 1:
        raise ValueError("max-tokens and timeout must be positive")
    if args.output.exists():
        raise ValueError(f"{args.output} already exists. Choose a new output path.")
    results = []
    for question in questions.values():
        print(f"Running {question['id']}...", file=sys.stderr, flush=True)
        results.append(infer(args, question))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        for row in results:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Saved {len(results)} predictions to {args.output}", file=sys.stderr)


def score(args, questions):
    predictions = indexed_rows(args.predictions)
    gold = json.loads((SAMPLES / "answers.json").read_text())
    if set(gold) != set(questions):
        raise ValueError("Reference answers and question IDs differ")
    extra = predictions.keys() - questions.keys()
    if extra:
        raise ValueError("Unknown prediction IDs: " + ", ".join(sorted(extra)))
    groups = {}
    items = []
    for key, question in questions.items():
        prediction = predictions.get(key, {"text": ""})
        text = prediction["text"]
        if not isinstance(text, str):
            raise TypeError(f"{key}: text must be a string")
        parsed = score_uniform(text, prediction.get("finish_reason", "stop"))
        choice = parsed["choice"]
        correct = choice == gold[key]
        for group in ("overall", question["task"]):
            result = groups.setdefault(group, {"correct": 0, "total": 0})
            result["correct"] += int(correct)
            result["total"] += 1
        items.append(
            {"id": key, "choice": choice, "gold": gold[key], "correct": correct}
        )
    for result in groups.values():
        result["accuracy_pct"] = round(100 * result["correct"] / result["total"], 2)
    print(
        json.dumps(
            {
                "scores": groups,
                "unanswered": sum(item["choice"] is None for item in items),
                "items": items,
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser(
        "predict", help="Send the four images and prompts to a vision model"
    )
    run.add_argument(
        "--base-url", required=True, help="API root, e.g. http://localhost:8000/v1"
    )
    run.add_argument(
        "--model", required=True, help="Vision model name served by the endpoint"
    )
    run.add_argument("--output", type=Path, required=True)
    run.add_argument(
        "--reasoning-effort", help="Optional effort supported by your server, e.g. none"
    )
    run.add_argument("--max-tokens", type=int, default=2048)
    run.add_argument("--timeout", type=int, default=300, help="Seconds per request")
    grade = commands.add_parser("score", help="Score saved predictions offline")
    grade.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()
    try:
        questions = indexed_rows(SAMPLES / "questions.jsonl")
        if args.command == "predict":
            predict(args, questions)
        else:
            score(args, questions)
    except (OSError, URLError, ValueError, KeyError, IndexError, TypeError) as exc:
        parser.exit(1, f"crosspanel: {exc}\n")


if __name__ == "__main__":
    main()
