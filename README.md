# Bukku MCP Server

MCP server connecting Claude to Bukku accounting (bukku.my).

## Tools available
- `get_invoices` — list invoices with date/status filters
- `get_invoice` — single invoice detail
- `get_overdue_invoices` — all overdue invoices
- `get_payments` — received payments
- `get_contacts` — customer/supplier list
- `get_journal_entries` — journal entries for P&L analysis
- `get_accounts` — chart of accounts
- `get_sales_summary` — total invoiced, paid, outstanding, overdue

## Deploy to Railway

### 1. Push to GitHub
Create a new GitHub repo and push all files:
```
git init
git add .
git commit -m "Bukku MCP server"
git remote add origin https://github.com/YOUR_USERNAME/bukku-mcp.git
git push -u origin main
```

### 2. Deploy on Railway
1. Go to railway.app → New Project → Deploy from GitHub repo
2. Select your bukku-mcp repo
3. Go to Variables tab and add:
   - `BUKKU_TOKEN` = your Bukku API token
   - `BUKKU_SUBDOMAIN` = retailedge
   - `PORT` = 8000
4. Go to Settings → Networking → Generate Domain
5. Copy the public URL (e.g. https://bukku-mcp-production.up.railway.app)

### 3. Connect to Claude
1. Claude.ai → Settings → Connectors → Add custom connector
2. Name: Bukku
3. URL: https://YOUR-RAILWAY-URL/mcp
4. Save and authorize
