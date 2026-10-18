# agentcontentkit.pro

Landing page, free PDF guide (email-gated), Agent Content Kit sales page, thank-you and privacy pages.
One container: nginx serves `site/` on port 80 and proxies `/api/` to a small Python (stdlib) lead API.

## Pages
- `/` free guide: email form, then the PDF downloads instantly
- `/kit/` sales page. Set `window.BUY_URL` in `site/kit/index.html` to the lava.top product link; empty = early-list mode
- `/thanks/` page after purchase (set as the success URL in lava.top)
- `/privacy/`

## Deploy (Easypanel)
1. Service → Mounts: add a **Volume** mounted at `/data` (leads live in `/data/leads.db`; without it they are lost on redeploy).
2. Service → Environment: `ADMIN_TOKEN=<long random string>`. Optional `WEBHOOK_URL=<url>` to copy every lead to another tool.
3. Deploy. Check `https://agentcontentkit.pro/api/health`.

## Leads
Download CSV: `https://agentcontentkit.pro/api/leads.csv?token=<ADMIN_TOKEN>`
