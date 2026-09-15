# Local demo API

This is a fictional event registration service for a short interview exercise.
All seed guests and email addresses are fictional. Data lives in memory and
resets whenever the process restarts. This is not a production service.

From this directory:

```sh
uv sync
uv run uvicorn app:app --host 127.0.0.1 --port 8000
```

Use a single worker. The lock protects operations within one process; separate
workers would each have their own data. API documentation is available at
`http://127.0.0.1:8000/docs`.

Run the existing baseline tests:

```sh
uv run pytest -q
```

Available routes:

| Method | Path | Result |
| --- | --- | --- |
| GET | `/api/health` | Local demo status |
| GET | `/api/events` | `{ "items": Event[] }` |
| GET | `/api/events/{id}/registrations` | `{ "items": Registration[] }` |
| POST | `/api/events/{id}/registrations` | New registration; status 201 |
| POST | `/api/demo/reset` | Restore the original fictional data |

New registration bodies contain `name` and `email`. Duplicate active emails
within one event and full events return 409. Missing events return 404, and
invalid input returns 422. Event counts are derived from active registrations.

To demonstrate a recoverable server failure, send `X-Demo-Fail: 1` on a write
request. It returns 503 without changing memory. Read requests are unaffected.
