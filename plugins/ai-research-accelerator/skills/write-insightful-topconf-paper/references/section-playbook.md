# Section Playbook

## Contents

1. Writing order
2. Abstract and title
3. Introduction and motivation
4. Related work
5. Method
6. Experiments
7. Limitations and conclusion

## Writing order

Do not default to article order. Prefer:

1. freeze notation and method;
2. write experimental protocol and verified results;
3. write limitations and scope;
4. stabilize the story chain;
5. write motivation and introduction;
6. position related work;
7. write conclusion, abstract, and title last.

## Abstract and title

### Abstract

Use five moves, usually in one paragraph:

1. important problem and current approach;
2. precise limitation or unexplained observation;
3. core insight;
4. method implied by the insight;
5. strongest evidence and bounded significance.

Do not spend scarce words on generic field background. Include numbers only when they are stable, comparable, and central.

### Title

Prefer a concrete subject plus the changed understanding or method. Avoid stacking slogans, unexplained acronyms, and broad claims. A reader should predict the paper's main question from the title.

## Introduction and motivation

The introduction should answer, in order:

1. What important task or failure matters?
2. What does current practice assume or require?
3. Which observations make that account insufficient?
4. What insight resolves the tension?
5. What design principle follows?
6. What method implements it?
7. Which experiments provide decisive support?

Use numbered Observation and Insight boxes only when they serve as anchors for this chain. Surround each box with prose that prepares it and explains its consequence. Never drop an isolated colored box into the paper.

Keep each callout to the shortest memorable statement, normally one sentence
and at most two. Put experimental values, protocol, caveats, and derivations in
the surrounding prose or in a referenced figure/table. A reader should be able
to scan only the callout titles and first sentences and recover the argument.
Every Insight callout must be a declarative, falsifiable claim. If its main verb
instructs the method to `use`, `apply`, `aggregate`, `restore`, or `define`
something, move that sentence to a design-principle paragraph and replace the
callout with the explanation from which the instruction follows.

When the motivation introduces a mathematical identity or objective property
that carries the story, state it as a labeled Lemma or Proposition and prove it.
Use the formal result for what is mathematically true, an Observation box for
what the evidence shows, and an Insight box for the interpretation that implies
the method. Do not merge these three roles into one rhetorical claim.

Follow each central formal result and proof with a brief reader-facing
explanation, integrated naturally into the prose rather than forced under an
`Intuition` heading. Keep routine short formulas inline; reserve displayed
equations for central objectives, derivations, and conclusions referenced later.

End the introduction with contributions that mirror the actual argument, not a generic list of features.

## Related work

Organize by the technical decision or limitation relevant to the paper, not by chronological paper summaries.

For each closest family, state:

```text
Shared objective or foundation -> key technical difference -> consequence -> evidence or citation
```

Do not claim novelty from memory. Name the closest work, verify it, and define the narrow delta. Distinguish "not studied," "not reported," and "not found in our search."

## Method

Write from principle to implementation:

1. state the target object or optimization goal;
2. derive the key relation with the minimum notation;
3. state the design principle motivated earlier;
4. introduce the simplest method satisfying it;
5. explain each component by the problem it solves;
6. provide the algorithm and computational cost;
7. state assumptions and reduction to familiar special cases.

Box only the equation that defines the paper's reusable object or central update. Explain it immediately in plain language.

Avoid presenting a sequence of equations without telling the reader what each changes conceptually.

## Experiments

Organize experiments by questions:

- **Effectiveness:** Does the method improve the target metric under fair budgets?
- **Efficiency:** Does it achieve the result per rollout, update, wall time, or compute?
- **Stability:** Does it avoid collapse across horizon, task, and seed?
- **Mechanism:** Does the predicted intermediate behavior occur?
- **Necessity:** Which component or principle is required?
- **Scope:** Does it transfer across models, rewards, data regimes, or modalities?

For every experiment, state:

```text
Question -> protocol -> metric -> result -> interpretation -> limit
```

Use compute-matched and data-matched baselines where relevant. Separate best checkpoint, final checkpoint, and area-under-curve claims. Do not choose evaluation conventions after seeing which favors the method.

Captions must be self-contained: define metrics, direction, uncertainty, budget, and the message the reader should verify.

## Limitations and conclusion

### Limitations

State demonstrated scope, unresolved mechanism, evaluation gaps, sensitivity, and costs. A precise limitation increases trust and prevents reviewers from defining a broader one.

### Conclusion

Do not repeat the abstract. Restate the changed understanding, the method it enabled, and the demonstrated boundary. End with the implication readers should carry into future work.
