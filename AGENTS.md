# OpenCode — AI Incident Intelligence V1

Target: implement V1 on the EXISTING microservices-python-demo codebase; do not create a new simulator.

Before making changes read `docs/00_DOCS_INDEX.md`, the V1 scope document, relevant architecture/flow, and current development stage. Inspect the actual source tree and confirm interfaces; documents do not prove code exists.

Rules:
- Manual incident trigger; local without Docker; read-only investigations; recommendations only.
- Preserve V0 behavior. Do not implement continuous monitoring, automated detection, auto-remediation, cloud/production adapters, Docker, or OpenTelemetry.
- Keep provider/tools as plain tested Python first. LangGraph after contracts. RAG then MCP once evidence-to-RCA baseline is working.
- Every RCA cites genuine incident evidence IDs, addresses contradictions, and permits `inconclusive`; bound retry/verification cycles to 3.
- Keep hidden evaluation ground truth inaccessible to the investigating agent and retrieval corpus.
- For each task: inspect code, propose minimal scope, implement only approved slice, run tests, report files/results and blockers.
- Do not guess nonexistent endpoints, paths or tools. Do not silently expand scope or refactor unrelated files.

Initial implementation task: inspect source tree, verify local V0 and tool signatures; then implement/test evidence models and incident state. If repository has no application code, report that blocker rather than generating an imaginary replacement.
