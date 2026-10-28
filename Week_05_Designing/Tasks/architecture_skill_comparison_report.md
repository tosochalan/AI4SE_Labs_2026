# Architecture Skill Comparison Report

## Summary

The fresh skill-guided run completed Task 1 and Task 2 in one recorded user turn and produced three viable options plus a proposed ADR. Its structure and decision hygiene were stronger and more consistent. Less prompts needed with the new skill implies higher speed, although it was not measured.

## Comparison

| Measure | With the [architecture-decision-record skill](../../.github/skills/architecture-decision-record/SKILL.md) | Without the skill (baseline) | Assessment |
|---|---|---|---|
| Completion speed | No exact start/end timer was captured. | The baseline files have different modification times, but they do not record when work began or ended. | **Not reliably measurable.** File timestamps are not comparable run-duration measurements. |
| Prompt turns | One recorded user task prompt covered both tasks; no clarification or revision prompt was needed in the fresh run. One prompt to rule them all. | More prompts needed for architecture proposals, an ADR first draft, and a finalization pass. | **Fewer iterations with the skill.** |
| Output quality | [ADR-002](./ADR-002.md) clearly separates evidence, assumptions, and open questions; evaluates three materially distinct options; keeps the recommendation **Proposed**; and covers consistency, authorization, retries, failure modes, and revisit triggers. | [ADR-001](./ADR-001.md) is also detailed and technically specific, including a concrete row-locking checkout strategy, persistent carts, and module-boundary controls. Its status is **Accepted**, though the notes do not record approval evidence. | **Skill run is more disciplined about uncertainty and decision status.** The baseline has deeper specificity in some implementation choices. |
| Overall efficiency | A complete comparison and ADR were produced from one recorded request, with no follow-up needed. | Requires multi-turn revisions and manual scaffolding across multiple prompts to establish structure and content. | **Promising improvement in interaction efficiency and repeatability; not a controlled comparison.** The fresh ADR is longer (235 lines versus 138), trading concision for broader coverage. |

## Conclusion and evidence limits

The skill appears to improve the consistency of architecture work: it prompts an evidence-based comparison, explicit assumptions, careful Proposed status, and a self-contained ADR. The fresh run was successful without iterative clarification. The result supports a qualitative efficiency/quality improvement, not a measured performance claim.

The skill file present and loaded for this run is [SKILL.md](../../.github/skills/architecture-decision-record/SKILL.md);
