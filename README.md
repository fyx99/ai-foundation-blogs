# ai-foundation-blogs

Blog posts and accompanying code on building governed Generative AI experiences on top of the SAP AI Foundation.

## Contents

- [`blog-governance-levels.md`](blog-governance-levels.md) -- *Govern the Generative AI Hub: Controlling Foundation Model Access on SAP BTP.* How CaaS gives you scoped credentials and deployment protection out of the box, and how a minimal proxy fills the remaining gaps when orchestration is shared. ([HTML version](blog-governance-levels.html) is the SAP Community-formatted output.)
- [`governance-proxy/`](governance-proxy/) -- runnable companion code for the post. A ~140-line FastAPI proxy that sits in front of AI Core orchestration and enforces a global model allowlist. Deployable to Cloud Foundry with a one-line `cf push`.

The proxy is intentionally minimal -- streaming, persistent token budgets, content-safety policy injection and per-tenant configuration are flagged in the blog as natural extensions but are not implemented here.
