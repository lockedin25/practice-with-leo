---
# The frontmatter is parsed by the content service. Do not place the full answer
# or unreleased facts in fields sent to the browser client.
case_id: example-original-profitability-001
title: Example original profitability case
status: draft
rights_status: original
source_id: internal-original
author: CaseCall content team
attribution: CaseCall original case
category: profitability
industry: consumer_goods
difficulty: foundation
target_duration_minutes: 30
interviewer_modes:
  - coached
  - realistic
  - pressure
competencies:
  - clarification
  - tailored_structure
  - quantitative_reasoning
  - business_judgement
  - synthesis
---

# {{title}}

## Candidate briefing

Use a short, original briefing with only the context the interviewer would give at
the start. It must state the client, the decision question and enough scope for the
candidate to ask useful clarifying questions.

## Case contract

| Field | Value |
|---|---|
| Decision question | What decision must the client make? |
| Success metric | How will success be measured? |
| Time horizon | What time period matters? |
| Candidate deliverable | Recommendation, rationale, risks and next step |
| Expected duration | 30 minutes |

## Interviewer-only runtime

> This section is private. The content compiler must split it from candidate-visible
> content and release only the active stage context to the interviewer.

### Stage 1 - Opening and clarification

**Stage goal:** Confirm that the candidate understands the objective and seeks only
high-value context.

**Initial statement:**

Write the exact original opening statement spoken by the interviewer.

**Allowed clarifications:**

| Candidate question class | Approved response | Why it matters |
|---|---|---|
| Objective and timeframe | Add the permitted fact | Tests problem definition |
| Scope and segments | Add the permitted fact | Tests prioritisation |
| Market versus company issue | Add the permitted fact | Helps direct the structure |

**Do not reveal yet:**

- Any fact that identifies the root cause.
- Future exhibits, answer paths or final recommendation.

**Advance when:**

- Candidate restates the objective and begins or requests time to structure.

### Stage 2 - Structure and first hypothesis

**Stage goal:** Assess whether the candidate forms a tailored, prioritised issue tree.

**Strong signals:**

- States an equation or causal structure appropriate to the case.
- Explains which branch they will test first and why.
- Communicates assumptions rather than silently making them.

**Recovery prompts:**

- `What would you examine first to isolate the largest driver?`
- `Can you make the structure specific to this client rather than list categories?`

**Advance when:**

- Candidate picks a logical first branch and asks for the required data.

### Stage 3 - Analysis and exhibits

**Stage goal:** Test calculation setup, interpretation and hypothesis revision.

#### Exhibit A

| Field | Value |
|---|---|
| Release condition | Candidate requests the relevant comparison or data cut |
| Candidate-visible title | Original, neutral title |
| Data | Link to a structured CSV or inline original table |
| Expected insight | What a strong candidate should notice |
| Common misread | The error the interviewer should probe |

**Interviewer rules:**

- Ask the candidate to interpret the exhibit before suggesting an insight.
- If arithmetic is wrong, ask for the setup or a sanity check before correcting it.
- Record an observation with evidence whenever the candidate materially succeeds or fails.

**Advance when:**

- Candidate identifies the key driver and its decision implication.

### Stage 4 - Recommendation

**Prompt:**

`Please give me your final recommendation. Start with your answer, then the two or three reasons behind it, the main risk, and the next step you would take.`

**Expected recommendation elements:**

1. Direct answer to the decision question.
2. Evidence from the case analysis.
3. A practical action plan.
4. A material risk or assumption.

## Answer key

> Private. Used by the evaluator after the candidate has given a final recommendation.

### Core diagnosis

Write the concise root cause and the evidence that proves it.

### Acceptable alternative paths

List valid routes to the answer. The evaluator must not penalise a candidate merely
for using a different structure.

### Expected calculations

| Calculation | Setup | Correct result | Tolerance |
|---|---|---|---|
| Example | Original formula | Original output | State rounding rule |

### Recommendations

| Priority | Recommendation | Rationale | Key risk |
|---|---|---|---|
| 1 | Original action | Why it addresses the diagnosis | What could fail |

## Evaluation rubric

| Competency | Developing | Competent | Strong | Evidence to capture |
|---|---|---|---|---|
| Clarification | Asks broad or low-value questions | Confirms objective and scope | Identifies the few facts that change the decision | Timestamp and question quality |
| Structure | Lists disconnected buckets | Creates a logical tree | Prioritises a tailored hypothesis-driven tree | Structure restatement |
| Quantitative reasoning | Calculation setup is unclear | Correct setup with minor errors | Clean setup, correct answer, sanity check | Calculation turn and result |
| Synthesis | Repeats analysis | Gives a conclusion | Gives answer, evidence, risk and next step | Final recommendation |

## Simulation quality checks

- [ ] A candidate can solve the case without material facts leaking early.
- [ ] A candidate can recover after one plausible wrong branch.
- [ ] Every approved response is factually consistent with the answer key.
- [ ] Every exhibit has an explicit release condition and expected insight.
- [ ] Full voice-mode and text-fallback simulations pass.
- [ ] Two human reviewers approve the content and interview flow.
