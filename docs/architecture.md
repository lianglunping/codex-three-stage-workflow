# Architecture

## Responsibility layers

```mermaid
flowchart LR
    A[Analyze: Sol read-only] -->|option selected| R[Refine: Sol read-only]
    R -->|scope approved| E[Execute: Terra staging writer]
    E --> C[Root CAS integrator]
    C --> S[Quiescent stable revision seal]
    S --> U[Sol read-only audit]
    U --> B[Revision-bound audit receipt]
```

An explicit Skill invocation or verifiable active run is the activation boundary.
The three-stage Skill owns task identity, approval, scope, and transitions only
inside that boundary; ordinary tasks retain normal model and tool access.
Supporting Skills own execution records, parallel-assignment safety, and audit
method. The JSON policy provides a shared machine-readable role contract only
for `explicit_skill_or_active_run`. The optional strict hook is an additional
declared-payload check for a dedicated session, not the source of user authority.

## Preventing planning loops

Analyze and Refine are bounded decision stages. Each uses one broad evidence
pass and at most one targeted gap-closing pass unless a named blocking unknown
can change the decision. Repeated issues receive a stable fingerprint and are
reported once when no new evidence appears. A `StageExitContract` makes the
exit condition explicit instead of allowing a strong planning model to expand
the task indefinitely.

## Preventing parallel write conflicts

Read-only reviewers can operate concurrently. A staging writer owns only
`coordination/staging/<assignment_id>/`. The root integrator applies accepted
bundles sequentially after checking the assignment, base revision, manifest
fingerprint, source hash, and target pre-hash. A stale base or changed source or
target rejects the integration without advancing the canonical revision.

Atomic replacement is per file. A hard crash between files is not a
multi-file transaction; verification and a new bounded integration pass remain
necessary for recovery.

## Seals and audit receipts

A seal requires no active work and two matching observations separated by a
stability window. Observations bind path, size, mtime at nanosecond precision,
and SHA-256. A later mtime-only change may remain metadata-only when byte hashes
still match; semantic or late-write drift invalidates the audit chain.

An audit receipt binds the exact revision id, manifest hash, scope fingerprint,
cutoff, auditor assignment, report hash, findings hash, verdict, and gate
statuses. A receipt for another revision is never treated as approval of the
current revision.
