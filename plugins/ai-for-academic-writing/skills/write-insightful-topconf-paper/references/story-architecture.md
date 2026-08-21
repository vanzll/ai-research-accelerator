# Story Architecture

## Contents

1. Reader transformation
2. The inevitability chain
3. Observation and Insight tests
4. Contribution compression
5. Common story failures

## Reader transformation

Define the paper by how it changes the reader's model:

```text
Before: What does the intended reader currently believe or do?
Friction: Which verified fact does that belief fail to explain?
After: What simpler or more accurate model should the reader leave with?
Action: What method or experimental practice follows from the new model?
```

A strong paper does not merely add a method. It makes the method easy to remember because it changes how the reader interprets the problem.

## The inevitability chain

Build one or more chains, but select one as primary:

```text
O1: Reproducible fact.
O2: Controlled contrast ruling out an easy explanation.
T: O1 and O2 conflict with the standard account.
I1: Minimal explanation that resolves the conflict.
D1: Requirement implied by I1.
M: Minimal mechanism satisfying D1.
P1: Outcome predicted by I1 and M.
E1: Experiment distinguishing P1 from alternatives.
```

Each arrow must be defensible:

- O1 -> T: state the prior expectation that O1 violates.
- T -> I1: compare at least one plausible alternative explanation.
- I1 -> D1: explain why the design requirement is necessary, not merely convenient.
- D1 -> M: separate the principle from this particular implementation.
- M -> P1: derive a measurable consequence.
- P1 -> E1: design a test that could fail.

If an arrow is weak, the paper needs reasoning or evidence there. Strong prose cannot repair it.

## Observation and Insight tests

### Observation test

An Observation must answer:

1. What exactly was measured or proved?
2. Against which control, baseline, or expectation?
3. Where is the evidence?
4. How large and repeatable is the effect?
5. What does it not establish?

Do not label a hypothesis, interpretation, or anecdote as an Observation.

### Insight test

An Insight is first of all a claim: a declarative proposition that can be true
or false. It should remain grammatical after `We argue that ...`, and a
skeptical reader should be able to describe evidence that would weaken it. It
should also satisfy most of these:

- explains more than one observation;
- compresses previously disconnected facts;
- rules out or weakens a common explanation;
- implies a concrete design principle;
- predicts a result not used to invent it;
- can be stated in one or two plain sentences;
- remains useful beyond the exact implementation.

Do not label a renamed mechanism, a result restatement, "X matters," an
imperative instruction, or a method step as an Insight. Sentences such as
`Aggregate evidence before the Jacobian` are design principles. State the
explanatory claim first, then derive such prescriptions from it.

## Contribution compression

Write the contribution at three resolutions:

```text
One sentence: We show [insight] and use it to [method/outcome].
Three sentences: problem/tension; insight; method plus decisive evidence.
One paragraph: prior practice; observations; insight; method; result; boundary.
```

If these versions disagree, the story is not stable.

Use a contribution hierarchy:

1. **Primary conceptual contribution:** the changed understanding.
2. **Primary technical contribution:** the mechanism implied by it.
3. **Empirical contribution:** evidence that validates both.
4. **Secondary capabilities:** only those that reinforce the primary thesis.

## Common story failures

- **Laundry-list paper:** several unrelated findings compete for attention. Choose one thesis and demote the rest.
- **Method-first motivation:** the introduction describes components before establishing why they are necessary. Move observations and tension earlier.
- **Retrofitted insight:** the claimed insight merely names the method. State an implementation-independent principle.
- **Fake inevitability:** the exposition implies experiments occurred in an invented order. Present a logical derivation without claiming chronology.
- **Benchmark-only novelty:** the paper wins but does not explain why. Add controlled observations and falsifiable mechanism tests.
- **Observation overload:** too many numbered observations dilute the main chain. Keep only those that force the method.
- **Insight inflation:** every paragraph is called an insight. Reserve the label for model-changing explanations.
- **Unsupported universality:** a result from one model or benchmark becomes a general law. State the demonstrated scope and the scaling hypothesis separately.
