# Design report

## Objective

The network converts a recursively discovered corpus of software-related
documents into a single traceable JSON requirements specification. It handles
plain text, Markdown, and email (`.eml`) inputs, retaining each source's
relative path so every retained or rejected candidate can be traced to evidence.

## Agentic network and rationale

The implementation uses LangGraph `StateGraph` so the process and its feedback
path are explicit. Four LLM roles use distinct models from the assignment's
available model set:

- **Extraction — GPT-4o mini:** identifies atomic requirements and relevant
  non-requirement material in corpus batches. The instruction explicitly
  requires broad coverage across functional, quality, data, reporting,
  operational, and constraint statements.
- **Synthesis — GPT-5 mini:** deduplicates semantically equivalent candidates,
  standardizes vocabulary, combines citations, assigns evidence-based
  priorities, and records disagreements rather than hiding them.
- **Review — GPT-5.6 Luna:** independently checks the draft against the source
  texts for completeness, consistency, duplicates, contradictions, priorities,
  and evidence.
- **Revision — GPT-5.4 nano:** addresses the review's concrete issues. The graph
  returns to deterministic validation and review, forming the required
  feedback loop, and has a finite configurable maximum number of review passes.

The deterministic nodes perform corpus discovery and email decoding,
batching, schema/source validation, exact duplicate merging, ID and priority
normalization, and final JSON serialization. If the revision model returns a
patch instead of a complete requirement, the revision node asks it to turn that
patch into a complete object while retaining unchanged requirements. Failures
in parsing, API calls, citations, or schema checks are surfaced rather than
converted into a success-shaped document. The revision stage also accepts
complete new requirements identified during review; they pass through the same
citation and priority checks and receive deterministic IDs.

## Requirement-spec coverage

| Assignment spec | Implementation |
|---|---|
| ANS1: at least 3 LLM nodes | Extract, synthesize, review, and revise nodes |
| ANS2: deterministic node | Loader, quality gate, and renderer |
| ANS3: feedback loop | Review → revision → quality gate → review |
| ANS4: at least 3 models | GPT-4o mini, GPT-5 mini, GPT-5.6 Luna, GPT-5.4 nano |
| ANS5: LangGraph | Explicit `StateGraph` workflow |
| OS1: one structured document | One JSON output file |
| OS2: unique IDs | Deterministic `REQ-nnn` IDs |
| OS3: no semantic duplicates | Synthesis and independent review; exact repeats also merged deterministically |
| OS4: tracing | Source-relative filenames attached to requirements and blacklist entries |
| OS5: name and paragraph | Extract/synthesis/review schema requires name and paragraph description |
| OS6: priority | Every requirement gets a defined scale value and rationale; scale is explained in output |
| OS7: consistency and contradictions | Synthesis and reviewer normalize terminology and flag conflicts for the blacklist |
| OS8: completeness | Batch extraction plus source-by-source reviewer coverage check |
| OS9: blacklist | Discarded irrelevant, nonsensical, or conflicting candidates have source and reason |

## Operational notes and limits

Set `OPENAI_API_KEY` in the environment before running. The run command takes an input directory, not individual filenames.
Model names may be overridden through environment variables for API deployments
with different model identifiers. The network's semantic judgments depend on
the selected models, so the reviewer and unresolved-issues section make
remaining uncertainty visible rather than claiming perfect completeness.

The environment used to prepare this submission did not contain an API key, so
the live LLM network could not be invoked to produce its final corpus output.
[`requirements.corpus-draft.json`](./requirements.corpus-draft.json) is a
clearly labeled, manually curated corpus draft and has not passed through the
agentic review loop. Running the documented command with a valid key produces
the actual network-generated JSON document.
