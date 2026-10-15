"""Client for the BGE-M3 query embedding API.

STATUS: VERIFIED live on 2026-10-14 with a real key against
http://44.194.201.67:3778/embed. Confirmed contract (this is a
HuggingFace Text Embeddings Inference server, given the x-compute-*/
x-tokenization-time/x-queue-time response headers):

  POST {EMBEDDING_API_URL}/embed
  Headers: Authorization: Bearer <key>, Content-Type: application/json
  Body:    {"inputs": "<text>"}          -- NOT "input", NO "model" field
  Response: a bare JSON list of vectors, one per input, e.g. for one input
            string: [[0.0879, 0.0179, ...]]  (1024 floats; matches the
            edariba_marketplace Qdrant collection's vector size exactly)

Earlier probes without a key got 401 on every call (including a bare GET /),
which is why this needed a real key before being implemented — guessing the
header/body shape from the task brief's illustrative example would have
been wrong on both the header style (Bearer was right) and the body field
name ("input" is wrong; it's "inputs").
"""

from typing import Any

import frappe
import requests

from edariba_marketplace.services.marketplace.config import (
	embedding_api_key,
	embedding_api_url,
	http_timeout_seconds,
)


class EmbeddingError(frappe.ValidationError):
	pass


def embed_text(text: str) -> list[float]:
	if not text or not text.strip():
		frappe.throw("Cannot embed an empty query.")

	url = f"{embedding_api_url()}/embed"
	key = embedding_api_key()  # throws clearly if unconfigured

	try:
		resp = requests.post(
			url,
			headers={
				"Authorization": f"Bearer {key}",
				"Content-Type": "application/json",
			},
			json={"inputs": text},
			timeout=http_timeout_seconds(),
		)
	except requests.exceptions.Timeout:
		frappe.log_error(title="Embedding API timeout", message=url)
		raise EmbeddingError("Search is temporarily unavailable (embedding timeout).")
	except requests.exceptions.RequestException as exc:
		# Never log `key` or `text` (may contain user PII) at error level.
		frappe.log_error(title="Embedding API request failed", message=f"{url}: {type(exc).__name__}")
		raise EmbeddingError("Search is temporarily unavailable.")

	if resp.status_code == 401:
		frappe.log_error(title="Embedding API auth rejected", message=url)
		raise EmbeddingError("Search is misconfigured (embedding auth rejected).")
	if resp.status_code >= 400:
		frappe.log_error(title="Embedding API error", message=f"{url}: {resp.status_code}")
		raise EmbeddingError("Search is temporarily unavailable.")

	vector = _extract_vector(resp.json())
	_validate_vector(vector)
	return vector


def _extract_vector(data: Any) -> Any:
	# Verified shape: a bare JSON list of vectors, one per input string.
	# We always send a single input, so we take the first (and only) row.
	if isinstance(data, list) and data and isinstance(data[0], list):
		return data[0]
	frappe.log_error(title="Unrecognized embedding response shape", message=str(data)[:500])
	raise EmbeddingError("Search is temporarily unavailable (unrecognized embedding response).")


def _validate_vector(vector: Any) -> None:
	if not isinstance(vector, list) or not vector:
		raise EmbeddingError("Embedding service returned an empty or invalid vector.")
	if not all(isinstance(v, (int, float)) for v in vector):
		raise EmbeddingError("Embedding service returned a non-numeric vector.")
