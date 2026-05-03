import platform
import base64
import requests
import urllib3
from datetime import datetime
from fastmcp import FastMCP
import pandas as pd
from rapidfuzz import fuzz

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

mcp = FastMCP("my-local-mcp-server")

df = pd.read_excel("Book1.xlsx")
records = df.to_dict(orient="records")

TICKET_BASE_URL = "http://localhost:8765"


# ─── Existing tools ────────────────────────────────────────────────────────────

@mcp.tool()
def ping(message: str = "") -> str:
    """Simple ping to verify the server is alive."""
    return f"pong: {message}" if message else "pong"


@mcp.tool()
def get_system_info() -> dict:
    """Returns basic system and environment information."""
    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "time": datetime.now().isoformat(),
        "node": platform.node(),
    }


@mcp.tool()
def get_device_config(admin_ip: str) -> dict:
    """
    Fetches the INI configuration file from a device using its Admin IP address.
    Always use the 'Admin IP address' field from search_equipment results — NOT the Host IP.
    """
    username = "puso7259"
    password = "Rw49iuMzJm"
    encoded = base64.b64encode(f"{username}:{password}".encode("ascii")).decode("ascii")
    url = f"https://{admin_ip}/api/v1/files/ini"
    try:
        response = requests.get(url, headers={"Authorization": f"Basic {encoded}"}, verify=False, timeout=15)
        try:
            data = response.json()
        except Exception:
            data = response.text
        return {"status_code": response.status_code, "data": data}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to device at {admin_ip}"}
    except requests.exceptions.Timeout:
        return {"error": f"Connection timed out after 15 seconds ({admin_ip})"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_active_alarms(admin_ip: str) -> dict:
    """
    Fetches active alarms from a device using its Admin IP address.
    Always use the 'Admin IP address' field from search_equipment results — NOT the Host IP.
    """
    username = "puso7259"
    password = "Rw49iuMzJm"
    encoded = base64.b64encode(f"{username}:{password}".encode("ascii")).decode("ascii")
    url = f"https://{admin_ip}/api/v1/alarms/active"
    try:
        response = requests.get(url, headers={"Authorization": f"Basic {encoded}"}, verify=False, timeout=15)
        try:
            data = response.json()
        except Exception:
            data = response.text
        return {"status_code": response.status_code, "data": data}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to device at {admin_ip}"}
    except requests.exceptions.Timeout:
        return {"error": f"Connection timed out after 15 seconds ({admin_ip})"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_equipment(query: str, field: str = "all") -> list[dict]:
    """
    Search equipment inventory by any field using fuzzy matching.
    Returns top 5 matches with confidence scores.

    WORKFLOW INSTRUCTIONS FOR AI:
    - If only 1 result is returned: proceed directly to the requested action using its 'Admin IP address'.
    - If multiple results are returned: present the list to the user and ask them to pick one.
    - Always use 'Admin IP address' (never 'Host IP address') for device API calls.
    """
    ALL_FIELDS = [
        "Equipment", "Equipment Reference", "Region", "Country", "Country Name",
        "Chassis Family Type", "Customer code", "Customer Name",
        "Admin IP address", "Host IP address",
    ]
    query = query.strip().lower()
    search_fields = [field] if field != "all" else ALL_FIELDS
    results = []
    for record in records:
        scores = [fuzz.partial_ratio(query, str(record.get(f, "")).lower()) for f in search_fields]
        best_score = max(scores)
        if best_score >= 70:
            results.append({**record, "_match_score": best_score})
    results.sort(key=lambda x: x["_match_score"], reverse=True)
    return results[:5]


# ─── Ticketing System Tools ────────────────────────────────────────────────────

@mcp.tool()
def Open_CriticalTicket(
    admin_ip: str,
    issue_description: str,
    priority: str = "critical",
    assigned_engineer: str = ""
) -> dict:
    """
    Opens a new incident ticket in the NOC ticketing system.

    INSTRUCTIONS FOR AI:
    - 'admin_ip': use the 'Admin IP address' from search_equipment. Never use Host IP.
    - 'issue_description': summarize the problem clearly.
    - 'priority': one of 'critical', 'high', 'medium', 'low'. Default is 'critical'.
    - 'assigned_engineer': optional.

    Returns the Incident ID. The customer can later use get_ticket_status or
    add_customer_update to follow up on this incident.
    """
    payload = {
        "device_ip": admin_ip,
        "description": issue_description,
        "priority": priority,
        "assigned_engineer": assigned_engineer or None,
    }
    try:
        response = requests.post(f"{TICKET_BASE_URL}/api/tickets", json=payload, timeout=10)
        ticket = response.json()
        return {
            "Incident ID": ticket["id"],
            "Status": ticket["status"],
            "Device IP": ticket["device_ip"],
            "Priority": ticket["priority"],
            "Issue Description": ticket["description"],
            "Assigned Engineer": ticket.get("assigned_engineer") or "Unassigned",
            "Created At": ticket["created_at"],
            "Message": f"Ticket {ticket['id']} opened. The customer can ask for updates or add information at any time."
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to ticketing system. Is it running on localhost:8765?"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_ticket_status(incident_id: str) -> dict:
    """
    Retrieves the full status and all updates for an incident — including updates
    posted by engineers via the NOC desk GUI.

    Use this when the customer asks:
    - "What's the update on INC000001?"
    - "Any progress on my ticket?"
    - "Has the engineer done anything yet?"
    - "What's the status of my issue?"

    The response includes ALL activity: engineer notes, status changes, and customer additions.
    Summarize the latest engineer update clearly for the customer.

    'incident_id' format: INC followed by 6 digits, e.g. INC000001
    """
    try:
        response = requests.get(f"{TICKET_BASE_URL}/api/tickets/{incident_id}", timeout=10)
        if response.status_code == 404:
            return {"error": f"Ticket {incident_id} not found."}
        ticket = response.json()

        updates = ticket.get("updates", [])
        engineer_updates = [u for u in updates if u.get("source") != "customer"]
        customer_updates = [u for u in updates if u.get("source") == "customer"]

        latest_engineer_update = engineer_updates[-1] if engineer_updates else None
        latest_customer_update = customer_updates[-1] if customer_updates else None

        return {
            "Incident ID": ticket["id"],
            "Current Status": ticket["status"],
            "Device IP": ticket["device_ip"],
            "Priority": ticket["priority"],
            "Issue Description": ticket["description"],
            "Assigned Engineer": ticket.get("assigned_engineer") or "Unassigned",
            "Opened At": ticket["created_at"],
            "Last Updated": ticket.get("updated_at") or "Not yet updated",
            "Total Updates": len(updates),
            "Latest Engineer Update": latest_engineer_update,
            "Latest Customer Addition": latest_customer_update,
            "Full Activity Log": updates,
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to ticketing system. Is it running on localhost:8765?"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_customer_update(
    incident_id: str,
    update_text: str,
    customer_name: str = ""
) -> dict:
    """
    Adds a message or additional information from the CUSTOMER to an existing ticket.
    This appears in the NOC desk GUI clearly marked as coming from the customer side.

    Use this when the customer wants to:
    - Add more information about their issue
    - Confirm whether a fix worked or not
    - Ask a follow-up question that the engineer should see
    - Report that the issue is still ongoing after an engineer update

    Examples:
    - "I want to add that the issue started after the maintenance window"
    - "Tell the engineer the SIP trunk is still down after the reboot"
    - "I need to inform them that this is also affecting site B"

    'incident_id': e.g. INC000001
    'update_text': the customer's message or additional info
    'customer_name': optional name of the customer contact
    """
    payload = {
        "text": update_text,
        "engineer": customer_name or "Customer",
        "source": "customer",
    }
    try:
        response = requests.post(
            f"{TICKET_BASE_URL}/api/tickets/{incident_id}/update",
            json=payload,
            timeout=10
        )
        if response.status_code == 404:
            return {"error": f"Ticket {incident_id} not found."}
        ticket = response.json()
        return {
            "Incident ID": ticket["id"],
            "Status": ticket["status"],
            "Your Update": update_text,
            "Posted By": customer_name or "Customer",
            "Timestamp": ticket["updated_at"],
            "Message": f"Your update has been added to {incident_id} and is now visible to the NOC engineer handling your case.",
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to ticketing system. Is it running on localhost:8765?"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_ticket_update(
    incident_id: str,
    update_text: str,
    engineer: str = "",
    new_status: str = ""
) -> dict:
    """
    Adds a progress update from an ENGINEER to an existing ticket and optionally changes status.

    Use this when an engineer or agent needs to log an action taken on a ticket
    (e.g., after running get_active_alarms, get_device_config, or doing a fix).

    - 'incident_id': e.g. INC000001
    - 'update_text': what was done or found
    - 'engineer': name of the engineer
    - 'new_status': optionally change to: open, in_progress, resolved, closed
    """
    payload = {
        "text": update_text,
        "engineer": engineer or "",
        "source": "engineer",
    }
    if new_status:
        payload["status"] = new_status
    try:
        response = requests.post(
            f"{TICKET_BASE_URL}/api/tickets/{incident_id}/update",
            json=payload, timeout=10
        )
        if response.status_code == 404:
            return {"error": f"Ticket {incident_id} not found."}
        ticket = response.json()
        return {
            "Incident ID": ticket["id"],
            "Status": ticket["status"],
            "Last Update Posted": ticket["updates"][-1] if ticket["updates"] else None,
            "Message": f"Engineer update posted to {incident_id}.",
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to ticketing system. Is it running on localhost:8765?"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_open_tickets() -> list[dict]:
    """
    Returns all open or in-progress tickets from the NOC ticketing system.

    Use when asked:
    - "What tickets are open?"
    - "Show me the incident queue"
    - "Any active incidents?"
    """
    try:
        response = requests.get(f"{TICKET_BASE_URL}/api/tickets", timeout=10)
        all_tickets = response.json()
        open_tickets = [t for t in all_tickets if t["status"] in ("open", "in_progress")]
        return [
            {
                "Incident ID": t["id"],
                "Status": t["status"],
                "Device IP": t["device_ip"],
                "Priority": t["priority"],
                "Issue": t["description"],
                "Engineer": t.get("assigned_engineer") or "Unassigned",
                "Created At": t["created_at"],
            }
            for t in open_tickets
        ]
    except requests.exceptions.ConnectionError:
        return [{"error": "Cannot connect to ticketing system. Is it running on localhost:8765?"}]
    except Exception as e:
        return [{"error": str(e)}]
