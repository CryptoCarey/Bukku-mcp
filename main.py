import os
import httpx
from typing import Optional
from mcp.server.fastmcp import FastMCP

# --- Config ---
BUKKU_TOKEN = os.environ["BUKKU_TOKEN"]
BUKKU_SUBDOMAIN = os.environ["BUKKU_SUBDOMAIN"]
BASE_URL = f"https://api.bukku.my/{BUKKU_SUBDOMAIN}"
HEADERS = {"Authorization": f"Bearer {BUKKU_TOKEN}"}

# stateless_http=True serves at root path, no OAuth required
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
    """
    List sales invoices from Bukku.
    - date_from / date_to: filter by date range (YYYY-MM-DD)
    - status: e.g. 'unpaid', 'paid', 'overdue', 'draft'
    - contact_name: filter by customer name
    """
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
    """List journal entries for P&L analysis, filtered by date range."""
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Get the app - stateless_http=True makes it serve at / root
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
