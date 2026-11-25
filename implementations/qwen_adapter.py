"""Test-only Qwen external adapter: line-delimited JSON over stdio.

Loads the pinned Qwen3-0.6B checkpoint on CPU, verifies the weights digest
at startup, and serves generation requests through the worker wire
protocol. Sampling comes from each request (never invented locally);
unparseable requests and generation failures return {"ok": false}.
The result is the first generated line (declared framing).
Feasibility probe only: no confirmatory claims.

Usage: python -m implementations.qwen_adapter --model-dir DIR --artifact DIGEST
"""
import argparse
import hashlib
import json
import sys
import time


def sha256_file(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


DEFAULT_PROMPT = (
    "Convert the request to a JSON object with keys operation and values. "
    "Reply with ONLY the JSON object, no other text.\nRequest: {input}"
)
DEFAULT_PROMPT_VERSION = "qwen-probe-v0"


def render_prompt(template, value):
    """Single-placeholder substitution: template JSON braces are literal."""
    return template.replace("{input}", value)


def load(model_dir, artifact):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    weights = str(model_dir / "model.safetensors")
    actual = sha256_file(weights)
    if actual != artifact:
        raise SystemExit(f"adapter artifact mismatch: weights hash {actual} != pin {artifact}")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir), dtype=torch.float32, trust_remote_code=False)
    model.eval()
    return model, tokenizer


def generate(model, tokenizer, value, sampling, template):
    import torch

    temperature = float(sampling.get("temperature", 0.0))
    top_p = float(sampling.get("top_p", 1.0))
    max_tokens = int(sampling.get("max_tokens", 64))
    seed = sampling.get("seed")
    if seed is not None:
        torch.manual_seed(int(seed))
    prompt = render_prompt(template, value)
    encoded = tokenizer(prompt, return_tensors="pt")
    started = time.perf_counter_ns()
    with torch.no_grad():
        out = model.generate(
            **encoded,
            max_new_tokens=max(1, min(max_tokens, 256)),
            do_sample=temperature > 0,
            temperature=max(temperature, 1e-6) if temperature > 0 else None,
            top_p=top_p if temperature > 0 else None,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(out[0][encoded["input_ids"].shape[1]:], skip_special_tokens=True)
    # Declared adapter semantics: the output is the first generated line. A
    # line-delimited channel needs a framing rule, and first-line framing is
    # the same for every draw, so it cannot inflate agreement counts.
    return text.split("\n", 1)[0], time.perf_counter_ns() - started


def answer(model, tokenizer, request, artifact, template, prompt_version):
    if request.get("artifact") != artifact:
        return {"ok": False, "error": "adapter artifact pin mismatch",
                "artifact": request.get("artifact")}
    try:
        result, compute_ns = generate(model, tokenizer, request.get("value"),
                                      request.get("sampling") or {}, template)
    except Exception as exc:  # noqa: BLE001 - adapter faults are provider failures
        return {"ok": False, "error": f"adapter generation failed: {exc}",
                "artifact": artifact}
    return {"ok": True, "result": result, "artifact": artifact, "compute_ns": compute_ns,
            "prompt_version": prompt_version}


def main(argv=None):
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--prompt-text", default=None)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    args = parser.parse_args(argv)
    template = args.prompt_text if args.prompt_text is not None else DEFAULT_PROMPT
    model, tokenizer = load(Path(args.model_dir), args.artifact)
    sys.stdout.write(json.dumps({"ready": True}) + "\n")
    sys.stdout.flush()
    def respond(request):
        return answer(model, tokenizer, request, args.artifact, template, args.prompt_version)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps({"ok": False, "error": "bad request"}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps(respond(request)) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
