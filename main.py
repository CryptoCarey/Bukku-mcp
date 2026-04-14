import os
import httpx
import secrets
from typing import Optional
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
from starlette.routing import Mount, Route

# --- Config ---
BUKKU_TOKEN = os.environ["BUKKU_TOKEN"]
BUKKU_SUBDOMAIN = os.environ["BUKKU_SUBDOMAIN"]
BASE_URL = f"https://api.bukku.my/{BUKKU_SUBDOMAIN}"
HEADERS = {"Authorization": f"Bearer {BUKKU_TOKEN}"}
SERVER_URL = os.environ.get("SERVER_URL", "https://web-production-ce3e2.up.railway.app")

mcp = FastMCP("Bukku", stateless_http=True)


def get(path: str, params: dict = {}) -> dict:
    url = f"{BASE_URL}{path}"
    r = httpx.get(url, headers=HEADERS, params={k: v for k, v in params.items() if v is not None}, timeout=15)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_invoices(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    contact_name: Optional[str] = None,
    per_page: int = 20
) -> dict:
    """List sales invoices. Status: unpaid, paid, overdue, draft. Date format: YYYY-MM-DD."""
    return get("/sales/invoices", {
        "date_from": date_from, "date_to": date_to,
        "status": status, "contact_name": contact_name, "per_page": per_page
    })


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Get full details of a single invoice by ID."""
    return get(f"/sales/invoices/{invoice_id}")


@mcp.tool()
def get_overdue_invoices(per_page: int = 50) -> dict:
    """Get all overdue invoices (unpaid past due date)."""
    return get("/sales/invoices", {"status": "overdue", "per_page": per_page})


@mcp.tool()
def get_payments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    per_page: int = 20
) -> dict:
    """List received payments filtered by date range (YYYY-MM-DD)."""
    return get("/sales/receipts", {"date_from": date_from, "date_to": date_to, "per_page": per_page})


@mcp.tool()
def get_contacts(name: Optional[str] = None, per_page: int = 30) -> dict:
    """List contacts (customers/suppliers), optionally filtered by name."""
    return get("/contacts", {"name": name, "per_page": per_page})


@mcp.tool()
def get_journal_entries(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    per_page: int = 20
) -> dict:
    """List journal entries for P&L analysis, filtered by date range (YYYY-MM-DD)."""
    return get("/journal_entries", {"date_from": date_from, "date_to": date_to, "per_page": per_page})


@mcp.tool()
def get_accounts(account_type: Optional[str] = None) -> dict:
    """List chart of accounts, optionally filtered by type (revenue, expense, asset)."""
    return get("/accounts", {"type": account_type})


@mcp.tool()
def get_sales_summary(date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """Get sales summary: total invoiced, paid, outstanding, and overdue amounts."""
    data = get("/sales/invoices", {"date_from": date_from, "date_to": date_to, "per_page": 100})
    invoices = data.get("data", [])
    overdue = [i for i in invoices if i.get("status") == "overdue"]
    return {
        "period": {"from": date_from, "to": date_to},
        "total_invoiced": round(sum(float(i.get("total", 0)) for i in invoices), 2),
        "total_paid": round(sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "paid"), 2),
        "total_outstanding": round(sum(float(i.get("balance_due", 0)) for i in invoices), 2),
        "invoice_count": len(invoices),
        "overdue_count": len(overdue),
        "overdue_amount": round(sum(float(i.get("balance_due", 0)) for i in overdue), 2)
    }


# --- OAuth endpoints (minimal, auto-approving) ---

async def oauth_protected_resource(request: Request):
    """Tell Claude this server uses OAuth."""
    return JSONResponse({
        "resource": SERVER_URL,
        "authorization_servers": [SERVER_URL]
    })


async def oauth_authorization_server(request: Request):
    """OAuth server metadata."""
    return JSONResponse({
        "issuer": SERVER_URL,
        "authorization_endpoint": f"{SERVER_URL}/oauth/authorize",
        "token_endpoint": f"{SERVER_URL}/oauth/token",
        "registration_endpoint": f"{SERVER_URL}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"]
    })


async def oauth_register(request: Request):
    """Dynamic client registration — auto-approve any client."""
    body = await request.json()
    client_id = secrets.token_urlsafe(16)
    return JSONResponse({
        "client_id": client_id,
        "client_secret": "not-needed",
        "redirect_uris": body.get("redirect_uris", []),
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none"
    }, status_code=201)


async def oauth_authorize(request: Request):
    """Auto-approve authorization — redirect straight back with code."""
    params = dict(request.query_params)
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")
    code = secrets.token_urlsafe(16)
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{separator}code={code}&state={state}")


async def oauth_token(request: Request):
    """Issue a token — just return a static one since we don't need real auth."""
    return JSONResponse({
        "access_token": "bukku-mcp-token",
        "token_type": "bearer",
        "expires_in": 86400
    })


mcp_app = mcp.streamable_http_app()

app = Starlette(routes=[
    Route("/.well-known/oauth-protected-resource", oauth_protected_resource),
    Route("/.well-known/oauth-authorization-server", oauth_authorization_server),
    Route("/oauth/register", oauth_register, methods=["POST"]),
    Route("/register", oauth_register, methods=["POST"]),
    Route("/oauth/authorize", oauth_authorize),
    Route("/oauth/token", oauth_token, methods=["POST"]),
    Mount("/", app=mcp_app),
])

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
