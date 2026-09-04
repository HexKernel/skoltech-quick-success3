"""Compact YOLOE visual embeddings for the three physical demo objects.

Generated from the user-provided reference photos in this order:
sponge, quail egg, piece of rock. Int8 quantization keeps the repository
artifact small while retaining the one-shot visual classification quality.
"""
from __future__ import annotations

import base64

import numpy as np

CLASS_NAMES = ["sponge", "quail egg", "piece of rock"]
SCALES = np.array(
    [0.0014287023805081844, 0.0015070789959281683, 0.0012778238160535693],
    dtype=np.float32,
).reshape(1, 3, 1)

DATA = (
    "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"
)


def embeddings():
    """Decode the quantized visual prompt tensor as a torch tensor."""
    import torch

    quantized = np.frombuffer(base64.b64decode(DATA), dtype=np.int8).reshape(1, 3, 512)
    return torch.from_numpy((quantized.astype(np.float32) * SCALES).copy())
