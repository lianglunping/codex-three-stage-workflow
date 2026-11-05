# Reviewable Three-Stage Deliverables

Use this reference to prepare or check a stage result. It specifies what the user
needs to decide and accept; it does not activate the workflow or grant authority.
Apply it to code, scientific analysis and document/figure work using the relevant
interfaces and evidence. Mark non-applicable dimensions with a short reason.

## Analyze: three detailed alternatives

Start with `【分析问题】`. Establish the goal, boundary conditions and acceptance;
search the relevant code, configuration and documentation needed to explain the
problem and upstream/downstream effects. Report observed causes separately from
hypotheses. A design task may have a constraint or unmet need rather than a defect.
Identify relevant duplication, architecture effects and maintenance debt without
expanding the work into an unrelated whole-repository cleanup. Ask for missing
decision-critical information before making a dependent recommendation.

Use **minimal change, balanced improvement, and substantial redesign** as a
preferred starting lens when those directions create meaningful tradeoffs. These
are not mandatory identities: if another distinction better fits the problem
(e.g. existing evidence, additional analysis, or new experiments), use it and
briefly explain why. Give each option a concrete name describing its actual method.
Do not merely rename three workload sizes or preselect the middle option.
Recommend from evidence, goals and constraints; a conservative or transformative
route may be best. All three must preserve data truthfulness and the validation
needed for the claims they make. Greater ambition never lowers evidence standards.

Present **方案 1、方案 2、方案 3**, each with the following substantive content:

1. **Approach and fit:** what this route does and which objective or constraint
   it prioritizes; explain the real difference from the other two.
2. **Mechanism and implementation:** explain the input-to-output flow and the
   components, files, configuration or scientific steps that would change. Give
   enough concrete detail to understand how it solves the actual problem.
3. **Scope and integration:** what is reused, what is introduced, interfaces and
   upstream/downstream effects, including relevant DRY opportunities.
4. **Benefits and limitations:** task-specific advantages, disadvantages and
   failure modes, including feasibility and dependencies.
5. **Costs and tradeoffs:** implementation complexity, performance implications,
   scalability, invasiveness, maintenance burden and technical debt. Use qualitative
   estimates with reasons when measurements or effort estimates are unavailable;
   do not invent timings, throughput, cost or certainty.
6. **Verification and recovery:** how success would be checked, the key failure
   case, and how the change could be reversed or isolated.
7. **Choose / avoid:** circumstances under which the user should select this
   route and circumstances that make it unsuitable.

Follow the three explanations with a comparison table on the same meaningful
dimensions and a recommendation tied to the user's constraints. Explain why the
recommended route beats the other two here and what evidence could change that
choice. Prefer the simplest sufficient route (KISS), not the fewest lines at the
expense of correctness or long-term maintenance. Consider a substantively different
route when it helps; do not challenge the user's premise just to tick a box.

Do not use three differently named versions of the same mechanism, exaggerated
disadvantages or deliberately inferior filler. If fewer than three feasible routes
exist under hard constraints, still explain the three genuinely examined paths,
identify which are conditional or rejected and why, and state how many are actually
selectable. Never present an invented third viable option. If evidence cannot
support three meaningful paths, report the specific gap and ask the needed question.

A table, three headings, or one-line pros/cons is not the required detail. No
arbitrary word count is needed: a reader should understand what changes, how it
works, what it costs, and why they might choose it without guessing implementation.
Do not generate implementation code, install dependencies, or silently select on
the user's behalf in MANUAL. End MANUAL Analyze awaiting the user's selection;
BOUNDED_AUTO records its supported selection and continues under existing authority.

## Refine: make the selected route executable

Start with `【细化方案】` and identify the selected option and selection evidence.
Expand only that option into:

- A complete planned file list: path, new/change/delete action, responsibility,
  per-file pseudocode or detailed behavioral change, and dependencies/order.
- Changed function signatures, class/module interfaces, data fields and contracts;
  for scientific work include relevant sample/reference/coordinate contracts.
- Boundary inputs, error handling, highest-risk changes, mitigations, backup and
  rollback. A developer unfamiliar with the conversation should be able to execute
  the plan without inventing the important decisions.
- The designated environment and any required local creation/installation. Reuse
  an existing suitable isolated environment, including venv/uv/Conda/container/HPC
  environment; when Python has none, specify project-local venv creation. For
  Node.js use the project's package manager and lockfile semantics.
- Concrete validation cases: input or trigger, expected behavior and pass condition.
  Identify existing QA commands from relevant project configuration and CI. Explain
  non-applicable categories; do not omit validation planning for non-code changes.
- Any temporary tests under an exclusive `temp_tests/<task_id>/` or task-owned
  scratch directory: exact ownership, when they run and removal after successful
  checks. Permanent regression tests stay in the project's normal suite.

Short signatures and pseudocode are permitted; complete executable implementations
are not. MANUAL waits for explicit approval of this refined plan in a later user
turn. BOUNDED_AUTO records scope, acceptance and transition evidence and continues.

## Execute: deliver and verify the agreed behavior

Start with `【执行方案】`. Execute only the approved scope in the designated
environment, including approved local setup if needed. Explicit interpreter paths
are equivalent to shell activation; do not assume activation persists between tool
calls. Read-only environment discovery does not require creating an environment.
Avoid global installs, unrelated features, automatic commits and development servers.

Discover and run the applicable configured formatting/style, lint/static analysis,
type, unit/integration and planned temporary checks. Distinguish PASS, FAIL,
NOT_RUN and not configured/applicable; explain unavailable required checks. Inspect
the real final artifact as appropriate. MANUAL pauses dependent execution on an
executed check failure, reports evidence and awaits the user's repair decision.
BOUNDED_AUTO repairs authorized failures and reruns affected checks. New runs
use evidence-backed renewable cycles from [repair-policy.md](repair-policy.md);
legacy/FIXED runs keep their limits. Neither mode can declare a failed required
check passed or use renewal to bypass scope, authority or real resource limits.

After checks pass, remove the exclusive temporary test directory created by this
task and verify it is gone. If unexpected/unrelated files appeared there, preserve
them and report the cleanup conflict rather than deleting them. Keep permanent
regressions and necessary failure evidence. Report actual behavior, checks, cleanup
and limitations; do not commit unless independently requested.

## Critical self-checks before each stage result

Review these internally; share conclusions and actionable gaps, not private
reasoning or a checkbox transcript. Address an applicable failed check before
advancing; if evidence or authority is missing, name the gap instead of pretending
every answer is affirmative.

- **Analyze:** Are the three routes materially different and explained well enough
  to choose? Are constraints/causes supported, assumptions explicit, relevant
  architecture/duplication considered, and KISS balanced with long-term robustness?
  Does the recommendation avoid both shortcutting and overdesign?
- **Refine:** Is every planned file's change understandable? Are interfaces,
  important edge cases, risks/mitigations, test expectations, environment and cleanup
  concrete? Is unnecessary coupling or intrusion avoided?
- **Execute:** Is the result readable and consistent with the project? Is any new
  debt disclosed? Were the designated environment and scope respected, temporary
  tests cleaned, and relevant correctness/security/performance/accessibility risks
  checked? Do current evidence and required acceptance support completion?
- **Before advancing:** Is the stage marker correct, work limited to the current
  stage, and the relevant MANUAL approval or BOUNDED_AUTO transition evidence present?

Detailed choices are a user decision aid. They do not authorize exhaustive research,
fabricated root-cause certainty, unrelated refactoring or new external actions.
