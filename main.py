import os
import httpx
from typing import Optional
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

# --- Config ---
BUKKU_TOKEN = os.environ["BUKKU_TOKEN"]
BUKKU_SUBDOMAIN = os.environ["BUKKU_SUBDOMAIN"]
BASE_URL = f"https://api.bukku.my/{BUKKU_SUBDOMAIN}"
HEADERS = {"Authorization": f"Bearer {BUKKU_TOKEN}"}

mcp = FastMCP("Bukku")


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
    - status: filter by invoice status e.g. 'unpaid', 'paid', 'overdue', 'draft'
    - contact_name: filter by customer name
    - per_page: number of results (max 100)
    """
    return get("/sales/invoices", {
        "date_from": date_from,
        "date_to": date_to,
        "status": status,
        "contact_name": contact_name,
        "per_page": per_page
    })


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Get full details of a single invoice by its ID."""
    return get(f"/sales/invoices/{invoice_id}")


@mcp.tool()
def get_overdue_invoices(per_page: int = 50) -> dict:
    """
    Get all overdue (unpaid past due date) invoices.
    Returns invoice number, customer, amount, due date.
    """
    return get("/sales/invoices", {
        "status": "overdue",
        "per_page": per_page
    })


@mcp.tool()
def get_payments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    per_page: int = 20
) -> dict:
    """
    List received payments.
    - date_from / date_to: filter by date range (YYYY-MM-DD)
    """
    return get("/sales/receipts", {
        "date_from": date_from,
        "date_to": date_to,
        "per_page": per_page
    })


@mcp.tool()
def get_contacts(
    name: Optional[str] = None,
    per_page: int = 30
) -> dict:
    """
    List contacts (customers/suppliers).
    - name: search by contact name
    """
    return get("/contacts", {
        "name": name,
        "per_page": per_page
    })


@mcp.tool()
def get_journal_entries(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    per_page: int = 20
) -> dict:
    """
    List journal entries for P&L and financial analysis.
    - date_from / date_to: filter by date range (YYYY-MM-DD)
    """
    return get("/journal_entries", {
        "date_from": date_from,
        "date_to": date_to,
        "per_page": per_page
    })


@mcp.tool()
def get_accounts(account_type: Optional[str] = None) -> dict:
    """
    List chart of accounts.
    - account_type: filter by type e.g. 'revenue', 'expense', 'asset'
    """
    return get("/accounts", {"type": account_type})


@mcp.tool()
def get_sales_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> dict:
    """
    Get a sales summary: total invoiced, total paid, total outstanding.
    Calculates from invoice data for a given date range.
    """
    data = get("/sales/invoices", {
        "date_from": date_from,
        "date_to": date_to,
        "per_page": 100
    })

    invoices = data.get("data", [])
    total_invoiced = sum(float(inv.get("total", 0)) for inv in invoices)
    total_paid = sum(float(inv.get("total", 0)) for inv in invoices if inv.get("status") == "paid")
    total_outstanding = sum(float(inv.get("balance_due", 0)) for inv in invoices)
    overdue = [inv for inv in invoices if inv.get("status") == "overdue"]

    return {
        "period": {"from": date_from, "to": date_to},
        "total_invoiced": round(total_invoiced, 2),
        "total_paid": round(total_paid, 2),
        "total_outstanding": round(total_outstanding, 2),
        "invoice_count": len(invoices),
        "overdue_count": len(overdue),
        "overdue_amount": round(sum(float(inv.get("balance_due", 0)) for inv in overdue), 2)
    }


# Mount at /mcp path for Claude connector
mcp_app = mcp.streamable_http_app()
app = Starlette(routes=[
    Mount("/mcp", app=mcp_app),
])

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
