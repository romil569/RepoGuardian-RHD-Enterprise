# Demo Script

Target length: 4-6 minutes.

## 1. Problem

"Open-source maintainers lose time triaging incomplete reports, duplicate issues, release regressions, and security-sensitive reports. Generic AI can be risky because it may invent evidence or take action too early."

## 2. Solution

"RepoGuardian is a maintainer assistant that syncs a real GitHub repository, builds repository-specific context, investigates issues with structured tools, and recommends actions that a human must approve."

## 3. Architecture

"The flow is GitHub sync, repository knowledge index, project-aware RAG, investigation orchestrator, structured analysis tools, evidence validation, action recommendation, human review, policy validation, and audit trail."

## 4. Live Repository

"This is the real demo repository `romil569/RepoGuardian-Demo`. The system has synchronized real issues, pull requests, releases, and comments."

## 5. Investigation

"For the incomplete issue, RepoGuardian identifies missing fields such as reproduction steps and logs. It recommends a request-more-information action, but does not post anything automatically."

## 6. Project-Aware RAG

"For the duplicate/regression issue, RepoGuardian retrieves repository-specific historical issues and release context. Evidence cards link back to verified GitHub sources."

## 7. Security Case

"For the API-key-in-logs issue, RepoGuardian treats it as security-sensitive and escalates to human security review. It avoids asking the reporter to publish secrets or exploit details."

## 8. Human Review

"The Review Queue shows the exact action preview and policy validation. AI recommends; the human controls external action."

## 9. Audit

"Every recommendation, approval, rejection, policy block, feedback item, and action result is recorded in the Audit Log."

## 10. Industry Roadmap

"The current hackathon build uses SQLite and local vectors for reliability. The enterprise path is GitHub App identity, webhooks, PostgreSQL and pgvector, queues, RBAC, SSO, multi-tenancy, managed secrets, observability, and audit retention."
