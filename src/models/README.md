# models/

Two checkpoints for BrainOS integration testing. The payloads live here and
are git-ignored (see the root `.gitignore`); only this policy file and
`manifest.json` are tracked. This directory is the W2 staging ground:
frozen external providers behind the existing contracts, outside the
standard-library kernel. `manifest.json` records identity, version,
digest, license, provenance, runtime requirements and expected BrainOS
contracts for each payload.

## Contents

| File | What it is | Source | Verified |
|------|-----------|--------|----------|
| `Qwen3-0.6B/` | Official smallest Qwen3 (0.6B params, safetensors, 311 tensors, ~1.4 GB). Fresh from Hugging Face 2026-11-23 — not the months-old Ollama copies. | `Qwen/Qwen3-0.6B` via `huggingface_hub.snapshot_download` | safetensors header parses, 311 tensors |
| `charactertest-closedloop-64167936-policy.npz` | Our motor policy: closed-loop candidate at 64,167,936 decisions (0.81 MB). Status: candidate (retention passed, acquisition unproven). | `Z:\charactertest\runs\continual_v2_closedloop_training\policy_64167936.npz` | SHA-256 matches registry: `222c4814…13a5` (`python -m checkpoints show current`) |

## Quick smoke test

```powershell
py -c "import numpy as np; d=np.load('models/charactertest-closedloop-64167936-policy.npz'); print({k:v.shape for k,v in d.items()})"
py -c "import json; print(json.load(open('models/Qwen3-0.6B/config.json'))['architectures'])"
```

## Intended use
Load the Qwen backbone as a frozen reasoning/perception specialist and
the motor policy as a frozen motor specialist behind BrainOS slot
contracts (`docs/current/02-formal-architecture.md` §2.8): same tensor
schemas, versioned adapters, supervisory gating — real checkpoints
through the toy-tested interfaces.
