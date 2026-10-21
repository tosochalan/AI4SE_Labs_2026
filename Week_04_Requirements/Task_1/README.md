# Task 1: Requirements refinement network

This LangGraph workflow reads a directory of `.txt`, `.eml`, and `.md` files and
writes one structured JSON requirements document. Input paths are discovered
recursively; no corpus filenames are hard-coded.

## Run

From this directory, install dependencies and copy the environment template:

```sh
python3 -m pip install -r requirements.txt
cp .env.example .env
# Edit .env and replace the placeholder with the API key you received.
python3 requirements_network.py data/corpus --output requirements.generated.json
```

The script loads `.env` from its own directory. Keep your actual `.env` private;
it is excluded from version control.

During a run, the terminal reports each stage, batch progress, model request,
review-loop activity, and output path. If a model call takes longer than 15
seconds, it prints a periodic waiting message with elapsed time.

Run the regression tests from this directory with:

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
```

The user-provided models are used across the LLM nodes. Override a default when
necessary with `REQUIREMENTS_EXTRACT_MODEL`, `REQUIREMENTS_SYNTHESIZE_MODEL`,
`REQUIREMENTS_REVIEW_MODEL`, or `REQUIREMENTS_REVISE_MODEL` environment
variables (see the constants near the top of the script); optional `OPENAI_BASE_URL`
is supported by the OpenAI SDK for compatible endpoints.

`requirements.corpus-draft.json` is a manually curated, source-grounded draft
included because no API key was configured during this task. It is not presented
as output from a live model run. The command above runs the network and writes
the actual generated document to `requirements.generated.json`.

## Network design

1. **Corpus loader (deterministic):** recursively reads supported documents,
   extracts plain text from email files, batches the corpus, and retains
   relative filenames for evidence tracing.
2. **Candidate extractor (GPT-4o mini):** identifies actionable requirements,
   candidate priorities, citations, uncertainties, and irrelevant/nonsensical
   material.
3. **Requirements synthesizer (GPT-5 mini):** merges semantically equivalent
   requests, standardizes language, preserves citations, and places conflicts
   into a blacklist rather than silently selecting a side.
4. **Deterministic quality gate:** validates schema and citations, assigns
   stable sequential IDs, normalizes priorities, and merges exact duplicates.
5. **Independent reviewer (GPT-5.6 Luna):** checks the full source corpus and
   draft for omissions, duplicate/conflicting requirements, traceability, and
   consistency.
6. **Revision agent (GPT-5.4 nano):** acts on review findings. The workflow
   loops through the quality gate and reviewer until approved or the configured
   review limit is reached; remaining issues are retained in the output.
7. **JSON renderer (deterministic):** writes a single document containing
   source documents, priority definitions, uniquely identified requirements,
   evidence citations, and a blacklist with reasons.

## Output contract

Each requirement includes a unique `REQ-nnn` ID, short name, paragraph
description, priority and rationale, and one or more source filenames. The
priority scale is included in the document; `Unspecified` avoids inventing a
priority unsupported by the corpus. Discarded irrelevant, conflicting, or
nonsensical candidates are recorded in `blacklist`. Reviewer issues remaining
at the review limit appear under `review.unresolved_issues`.

## Design report

See [DESIGN_REPORT.md](./DESIGN_REPORT.md) for the design rationale and
requirements-spec mapping, including the execution limitation for the included
corpus draft.
