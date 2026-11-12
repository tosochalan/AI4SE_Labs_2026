# Repository-Aware Source Code Generation: Proposed Pipeline

## Recommendation

Use a staged, repository-aware retrieval and validation pipeline rather than relying on embedding similarity alone. The assignment's fixed top-five retrieval is a useful baseline, but neither embeddings nor a fixed chunk count are universally best.

## Pipeline

1. **Understand the change.** Parse the task into the target symbol, required behavior, constraints, and likely affected files. Inspect the target's signature, docstring, imports, and nearby code.
2. **Build a structural index.** Parse source into symbol-level chunks (functions, methods, classes, and relevant documentation), retaining path, symbol, line range, and parent/child relationships. Keep chunks within token limits; split oversized symbols by logical blocks with overlap. Index tests, interfaces, and configuration separately. Refresh the index for the current repository revision and exclude generated, vendored, and irrelevant files.
3. **Retrieve and expand context.** Use a hybrid search: exact identifier/path and lexical search for code-specific terms, plus semantic embeddings for conceptual matches. Filter by language and repository scope, then rerank candidates using symbol names, imports, call relationships, and test relevance. Expand the best matches with directly related definitions, callers, and tests. Deduplicate and include only as much context as fits the model's token budget.
4. **Generate a focused patch.** Give the model the task, target code, relevant conventions, and selected context. Ask for a minimal diff rather than an unconstrained file rewrite.
5. **Validate before applying.** Check patch scope and syntax, run formatting/type checks and focused tests, then broader tests as appropriate. If validation fails, provide the specific diagnostics for a bounded repair attempt; show the final diff for review.

## Retrieval and Chunking Choices

Embeddings help find conceptually related code when task wording differs from repository terminology, but can miss exact identifiers and rank superficially similar code. They should complement, not replace, lexical/symbol search. The best number of chunks depends on task complexity and context size: retrieve a candidate pool, rerank it, and select relevant chunks to a token budget rather than always sending exactly five. AST- and symbol-aware boundaries preserve complete signatures and scope better than arbitrary fixed-size text chunks; relationship-based expansion supplies dependencies without flooding the prompt.

Evaluate retrieval and generation on representative repository tasks using relevant-context coverage, token usage, patch correctness, and test pass rate. Tune the ranking and context budget against those results; there is no universally optimal chunk count or retrieval method.