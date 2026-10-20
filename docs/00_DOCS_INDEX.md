# AI Incident Intelligence — V1 Documentation Index

**Current target:** V1 Reactive AI Incident Commander. Preserve the existing V0 simulator; V0 documentation and V2–V5 designs are not part of this active implementation package.

Read in order:

1. `02_V1_REACTIVE_INCIDENT_COMMANDER.md` — V1 goals and boundaries.
2. `ARCHITECTURE/01_SYSTEM_ARCHITECTURE.md` — overall architecture; later-version sections are informational only.
3. `ARCHITECTURE/02_LANGGRAPH_ARCHITECTURE.md` — incident graph and bounded verification.
4. `ARCHITECTURE/03_SUBGRAPHS_AND_AGENTS.md` — investigator responsibilities.
5. `ARCHITECTURE/04_INCIDENT_STATE_AND_EVIDENCE.md` — evidence and state contracts.
6. `FLOWS/01_END_TO_END_INCIDENT_FLOW.md`, `03_INVESTIGATION_FLOW.md`, `04_RCA_AND_VERIFICATION_FLOW.md`.
7. `ENVIRONMENTS/01_LOCAL_WITHOUT_DOCKER.md` — currently supported runtime.
8. `DEVELOPMENT/01_IMPLEMENTATION_PLAN.md` — staged delivery; stages 10–15 are future work.
9. `DEVELOPMENT/02_INCIDENT_SCENARIOS.md`, `03_EVALUATION_STRATEGY.md`, `04_CODING_AGENT_GUIDE.md`.
10. Read `ARCHITECTURE/05_MCP_ARCHITECTURE.md`, `06_RAG_ARCHITECTURE.md`, `07_LLM_AND_JEV.md` **when implementing those concerns**, not as prerequisites for initial working graph.

**Precedence:** V1 scope > current-stage implementation plan > V1 graph/evidence contracts > relevant flow > future-looking architecture. Real repository code must be inspected before claiming providers/routes already exist.

**V1 safety:** manual trigger, read-only tools, evidence-cited RCA or explicit inconclusive conclusion, maximum three verification cycles, no automatic remediation. Never let evaluation ground-truth documents reach tools, prompts, or RAG. Make changes in small testable slices.

## Future V3 multi-agent architecture (reference only)

`ARCHITECTURE/08_V3_DUAL_ORCHESTRATION_MULTI_AGENT.md` specifies two LangGraph orchestrations, specialist agents/subgraphs, deterministic aggregators, shared incident handoff, MCP/RAG/Jev boundaries, human-approved writes and the V3 delivery plan. **Not part of the active V1 implementation.**
