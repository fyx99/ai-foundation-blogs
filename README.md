# ai-foundation-blogs

Blog posts and accompanying code on building governed Generative AI experiences on top of the SAP AI Foundation.

Each post lives in its own folder at the repo root.

## Posts

- [**Govern the Generative AI Hub: Controlling Foundation Model Access on SAP BTP**](ai-core-governance-levels/blog.md) — How CaaS gives you scoped credentials and deployment protection out of the box, and how a minimal proxy fills the remaining gaps when orchestration is shared.
  Companion code: [`governance-proxy/`](ai-core-governance-levels/governance-proxy/) — a ~140-line FastAPI proxy enforcing a global model allowlist on AI Core orchestration. Deployable to Cloud Foundry with a one-line `cf push`.

## Rendering for the SAP Community

The Community editor expects HTML with `<li-code lang="...">` for code blocks. To regenerate `blog.html` from `blog.md`:

```bash
pip install markdown
python3 render_blog.py
```

The script also rewrites prose `--` to em-dashes (`—`) while leaving CLI flags inside code blocks alone.
