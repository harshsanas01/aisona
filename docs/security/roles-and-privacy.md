# Roles, access control, and privacy

This is a demo/pilot deployment: there is no real login flow, identity
provider, or session system. What exists is a **foundation** two things can
be built on top of later - role-based permission checks on the API, and a
privacy-by-default audit trail - documented here so both stay consistent as
the app grows.

## Roles and permissions

Roles and their permissions are defined once, in the domain layer
(`packages/domain/src/carecall_domain/services/access_control.py`), and
mirrored in the frontend (`apps/web/src/app/RoleContext.tsx`) purely for
UI gating - the frontend copy is never trusted for enforcement.

| Role | view | review | manage_tasks | developer_tools |
|---|---|---|---|---|
| `viewer` | yes | no | no | no |
| `coordinator` (default) | yes | yes | yes | no |
| `admin` | yes | yes | yes | yes |

- **view**: read timelines, patterns, person mentions, briefs, tasks; ask questions. Every role has this.
- **review**: confirm/correct/dismiss a timeline event, pattern, or person mention; submit feedback on an answer.
- **manage_tasks**: create/update/complete/reopen a coordinator task; generate/regenerate a brief; rebuild a patient's timeline/patterns/person mentions; ingest a call.
- **developer_tools**: defined for future use (e.g. per-user gating of the audit trail and Retrieval Comparison Lab). Today those two surfaces are gated solely by the deployment-level `CARECALL_DEVELOPER_MODE` flag, not by role - see "Known limitations" below.

## How the acting role travels

There is no session token. The frontend keeps the selected role in
`localStorage` (`carecall.role`, set via the role switcher in the header)
and sends it as a plain `X-CareCall-Role` request header. The API's
`require_permission(...)` FastAPI dependency
(`apps/api/src/carecall_api/access_control.py`) reads that header and
403s if the role lacks the required permission.

A request that sends no header at all - every pre-RBAC test, script, and
any future internal caller - is treated as `coordinator`
(`carecall_domain.services.access_control.DEFAULT_ROLE`). This is
deliberate: it's what every endpoint behaved as before RBAC existed, so
nothing that worked before this feature was added silently breaks.

This is a local-dev/demo mechanism, not authentication - a client can claim
any role by setting the header directly (there is no signing or session
verification). It is a foundation for real authentication to plug into
later (e.g. resolving the role from a verified session instead of a raw
header), not a production access-control system on its own.

## Known limitations

- No real identity provider, login, or session - "who is acting" is
  self-reported by the client.
- `developer_tools` is defined but not yet enforced per-request; the audit
  trail and Retrieval Comparison Lab are gated only by the deployment-wide
  `CARECALL_DEVELOPER_MODE` flag.
- No row-level/per-patient access scoping - any role that can view can view
  every patient's data.

## Privacy: the question-audit trail

`QuestionAudit` (see `packages/domain/src/carecall_domain/entities/question_audit.py`)
records everything needed to answer "why did the system produce this
answer?" - retrieval config, candidate/selected evidence ids, model/prompt
version, grounding check results - without ever storing the raw question or
transcript text in a standard log:

- The question is hashed (`question_hash`) by default.
- `question_preview` (a short, truncated excerpt) is only ever populated
  when a deployment explicitly opts in via
  `CARECALL_AUDIT_RETAIN_QUESTION_PREVIEW=true`.
- Feedback on an answer is looked up live from `Feedback` records
  (`target_type="answer"`, `target_id=request_id`) rather than stored on
  the audit row itself - the audit trail is append-only and never
  rewritten after creation.

## Coordinator/assignee identity

Task `assignee` and `created_by`/`actor` fields are always plain free text
(e.g. "Nurse Amy") - there is no user directory to validate them against.
Don't read a match against one of these strings as a verified identity
claim.
