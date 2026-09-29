# API contract

Base URL: the private `api_url` output from the OCI stack. All routes require
`Authorization: Bearer <api-key>`.

## `POST /v1/systemone`

Send `Content-Type: application/json` and `Accept: application/json`.

```json
{
  "model": "multilingual",
  "state": "The customer reports a duplicate charge.",
  "questions": {
    "team": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {"billing": "Payments", "technical": "Software faults"}
    },
    "urgency": {
      "type": "score",
      "instructions": "How urgent is this?",
      "criteria": ["low", "medium", "high"]
    },
    "refund_requested": {
      "type": "noul",
      "instructions": "Does the customer ask for a refund?"
    }
  }
}
```

The compatible response contains typed answers and probabilities. `choice`
selects a supplied criterion, `score` returns a score over supplied levels, and
`noul` returns yes/no/unknown. It does not generate text. The deployment pins
`model` to `multilingual`; other checkpoints are rejected. See the checked-in
English and Swedish synthetic request files.

Request limits: body 32 KiB, state 8,000 characters, up to 8 questions, 16 choice
options per question, 10 score levels, 64 total options, 512 model tokens, and two
admitted inference requests. Exact validation and status behavior follows the
pinned upstream Laya serving contract.

## `GET /health`

Authenticated readiness and release identity. It reports CPU execution, loaded
checkpoint and immutable model revision. Health does not prove response quality
or performance for your use case.

## `GET /docs` and `/openapi.json`

Authenticated API documentation and OpenAPI schema. No route is anonymously
accessible.
