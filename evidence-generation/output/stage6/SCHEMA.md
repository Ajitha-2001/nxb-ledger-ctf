# Stage 6 - data schema and example output

You are given three files here plus the Stage 5 evidence you already hold
(`app_access.csv`, `workstation_sessions.csv`). Python 3 standard library is enough
(`csv`, `json`, `base64`).

## messages.jsonl  (one JSON object per line, order is NOT meaningful)
| field | type | notes |
|---|---|---|
| message_id | string | unique message reference |
| sender_handle | string | chat handle, maps to `directory.csv` |
| application_id | string or null | application the message was tagged with |
| transaction_ref | string or null | payment reference, maps to `broker_ledger.csv` |
| body_b64 | string | Base64 of a UTF-8 message body |

## directory.csv
`handle, employee_id, full_name, branch` - `N/A` means the handle is not a bank employee.

## broker_ledger.csv
`tx_ref, broker_account, amount_lkr, date, note`

## Stage 5 files you will need to join
`app_access.csv`: `access_id, employee_id, application_id, session_id, timestamp_utc+0530`
`workstation_sessions.csv`: `session_id, employee_id, workstation_id, login_time_utc+0530, logout_time_utc+0530`

## Required output: evidence.json
A JSON object with exactly these six string fields (values below are PLACEHOLDERS, not the answer):

```json
{
  "employee_id": "EMP000",
  "application_id": "APP-0000",
  "workstation_id": "NXB-BR00-WS00",
  "session_id": "SES-000",
  "broker_transaction_ref": "TX-000",
  "message_id": "CHAT-00"
}
```

## Rules
* Several messages mention the target application. Only the chain that links an *employee*
  to a *payment record for that application* counts; explain at least one of your joins.
* Your script `correlate.py` must give the same result if the input rows are shuffled.
* Do not hard-code the answer values.
