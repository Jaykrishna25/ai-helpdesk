# UniAssist — Cloud-Based Multi-Agent AI Student Help Desk

A production-oriented reference implementation of a multi-agent, RAG-powered help desk that
answers student queries from a governed knowledge base and auto-escalates uncertain ones to
faculty — then learns from every resolution.

> **Design document:** [`docs/DESIGN.md`](docs/DESIGN.md) covers all 20 enterprise deliverables
> (architecture, agents, NLP, DB/ER, AWS, conversation design, flowcharts, wireframes, security,
> governance). Diagrams render on GitHub/VS Code (Mermaid).

## What's inside
```
ai-helpdesk/
├── backend/          FastAPI app: 12 AI agents, RAG engine, auth, APIs
│   ├── app/agents/   intent, entity, retrieval, rag, confidence, decision,
│   │                 routing, ticket, notification, learning, analytics, security
│   ├── app/rag/      embeddings + vector store
│   └── test_core.py  standalone verification of the AI core (no external deps)
├── frontend/         Single-page portals: student · faculty · admin
├── database/         PostgreSQL 15 + pgvector schema
├── infra/terraform/  AWS IaC: ECS Fargate, RDS, OpenSearch, Cognito, SES, SQS, WAF, IAM
├── docker-compose.yml
└── docs/DESIGN.md    Full 20-deliverable design document
```

## The core loop
1. Student asks a question → **Intent** + **Entity** agents parse it.
2. **Retrieval** finds top-K KB chunks; **RAG** grounds an answer; **Confidence** scores it as
   `0.4·Retrieval + 0.3·Similarity + 0.3·LLM`.
3. **Decision**: ≥ **85%** → answer & save chat; < 85% → **Routing** + **Ticket** + **Notification**.
4. Faculty answers → student emailed → **Learning** drafts a KB entry → admin approves → re-indexed
   → the next student is answered automatically.

## Run locally (SQLite, zero external services)
```bash
cd backend
python -m pip install -r requirements.txt
python -m app.seed_data              # create + seed the demo DB
uvicorn app.main:app --reload        # http://localhost:8000  (serves the portals too)
```
Demo logins — Student `21CS7042 / student123` · Faculty `F-EXAM-01 / faculty123` · Admin `ADMIN-01 / faculty123`.

Try in the Student portal: **"When will Semester 7 examinations begin?"** (answered by AI) and
**"Can I bring my pet dog to the fest afterparty?"** (escalated to a ticket).

## Verify the AI core without installing anything
```bash
cd backend && python test_core.py
```
This exercises normalization, intent classification, entity extraction, embedding retrieval,
the confidence formula, and the 85% decision — all on stdlib + numpy.

## Run production-like (Postgres + OpenSearch + Redis)
```bash
docker compose up --build      # API + pgvector + OpenSearch + Redis
```
Set `DATABASE_URL` to Postgres, `NOTIFY_BACKEND=ses`, and uncomment the production packages in
`requirements.txt` (sentence-transformers, psycopg2, pgvector, boto3) to enable real embeddings,
Postgres/pgvector, and SES email.

## Deploy to AWS
`infra/terraform/` provisions a multi-AZ, auto-scaling stack (ECS Fargate + RDS Multi-AZ +
OpenSearch + Cognito + SES + SQS + WAF + least-privilege IAM). Review CIDRs, sizing, and IAM
before `terraform apply`.

## Notes on the reference build
- The demo embedding is a deterministic hashed bag-of-words vector so everything runs **offline**.
  Swapping in `all-MiniLM-L6-v2` or Bedrock Titan (same interface) sharpens confidence with no
  call-site changes.
- The RAG agent returns approved answers verbatim with citations, guaranteeing **no hallucination**
  in the demo; the production path plugs an LLM behind the same grounding contract.

## License
Reference/educational architecture. Review security, privacy (FERPA/GDPR), and sizing before
real-world deployment.
