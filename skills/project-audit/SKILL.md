---
name: project-audit
description: >-
  Audit bioinformatics or scientific-analysis projects and delivery packages
  for evidence traceability, input integrity, genomic coordinate correctness,
  code and method reliability, semantic result validity, reproducibility,
  conclusion strength, and release consistency. Use when the user asks for a
  project audit, deliverable review, reproducibility check, pre-release or
  pre-submission inspection, or verification that code, tables, figures,
  documentation, and claims agree.
---

# Project Audit

Produce an evidence-based audit tied to inspectable files, commands, outputs,
logs, and source documents.

## Boundaries

- Audit and explain by default; do not remediate unless the user separately asks.
- Do not assume missing evidence exists elsewhere. Mark it MISSING.
- Classify evidence as VERIFIED, INFERRED, MISSING, or NOT_APPLICABLE.
- Distinguish execution success from semantic result validity.
- Match severity and conclusion strength to demonstrated impact.

## Workflow

1. Define the audit cutoff, entry point, scope, delivery profile, and available
   and missing materials.
2. Build an evidence inventory and input manifest before interpreting results.
3. Select applicable modules from references/audit-modules.md by project type
   and risk; do not run irrelevant checks mechanically.
4. Trace critical claims and numbers through code, tables, figures, reports,
   manifests, and release artifacts.
5. For genomic work, establish the assembly, annotation, contig, coordinate,
   strand, and REF/ALT contract before judging site-level results.
6. Run or reproduce only read-only or explicitly authorized checks. Preserve
   commands, versions, paths, and outputs used as audit evidence.
7. Use references/checklist.md to close gaps and
   references/output-template.md to report findings and acceptance gates.

## Audit a Sealed Revision

When present, use `<CODEX_HOME>/policies/three-stage-runtime-v1.json`
for machine-readable model and receipt-binding checks; it does not expand audit
write authority.

For multi-agent, pre-release, or mutable workspaces, do not audit an unbound
directory state. Require a quiescent sealed revision and record:

```text
revision_id, manifest_sha256, scope_fingerprint, audit_cutoff
```

The auditor uses role `AUDITOR`, has no canonical write scope, and reads the
same sealed material as any independent reviewer. A valid result is an audit
receipt bound to that revision and scope, not a free-standing statement that a
path once looked correct.

Immediately before reporting or reusing a receipt, verify the sealed manifest.
If canonical files changed after the cutoff, classify the drift as
metadata-only, semantic in-scope, out-of-scope, or late-write. Semantic or
late-write drift invalidates the receipt; re-audit the minimal affected
dependency chain. Do not trigger a full audit solely from mtime change when the
registered semantic equivalence rule still passes.

## Risk-Scaled Independent Review

- Use one primary audit for ordinary scope.
- Add independent review for high-risk, cross-domain, conclusion-sensitive,
  pre-release work, or when the user asks for it.
- Give reviewers the same scope and source materials.
- Choose reviewer roles and count from the risk; never bind the workflow to a
  model brand or fixed number.
- Resolve disagreements from evidence and record the rationale.
- Bind every independent review to the same `revision_id`, manifest, scope, and
  cutoff; a review of another revision is not a vote on the current one.

## Acceptance Rule

Do not declare Ready merely because commands exited successfully or files
exist. Require the applicable input-integrity, traceability, semantic-QA,
coordinate-contract, cross-format, reproducibility, and release gates to pass.
Any unresolved Critical finding blocks Ready.
Any unresolved Major finding that causes an applicable gate to fail or remain
unverified also blocks Ready.
For a revision-bound audit, a missing, invalid, stale, or drifted audit receipt
also blocks Ready.
