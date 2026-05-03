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


# ─── Device tools (unchanged) ─────────────────────────────────────────────────

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


# ─── CUSTOMER-FACING Ticketing Tools ──────────────────────────────────────────
#
# IMPORTANT DESIGN RULE:
#   - These tools are for CUSTOMERS talking to the Foundry agent ONLY.
#   - Engineers do NOT use MCP. Engineers work exclusively in the Flask GUI.
#   - Customers can: open tickets, retrieve engineer updates, add info to a ticket.
#   - Customers CANNOT change ticket status — only the engineer can via the GUI.
#
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def Open_CriticalTicket(
    admin_ip: str,
    issue_description: str,
    priority: str = "critical",
    customer_name: str = ""
) -> dict:
    """
    Opens a new incident ticket on behalf of the CUSTOMER.

    INSTRUCTIONS FOR AI:
    - 'admin_ip': use the 'Admin IP address' from search_equipment. Never use Host IP.
    - 'issue_description': summarize the problem the customer described.
      If unclear, ask the customer to describe it before calling this.
    - 'priority': one of 'critical', 'high', 'medium', 'low'. Default 'critical'.
    - 'customer_name': name of the customer contact if known.

    After opening, tell the customer their Incident ID and that they can:
    - Ask for updates at any time ("what's the status of INC000001?")
    - Add more information ("I want to add that...")
    The NOC engineer will be notified and handle the case from their desk.
    """
    payload = {
        "device_ip": admin_ip,
        "description": issue_description,
        "priority": priority,
        "assigned_engineer": None,
    }
    try:
        response = requests.post(f"{TICKET_BASE_URL}/api/tickets", json=payload, timeout=10)
        ticket = response.json()

        # Log the opening as a customer entry in the activity log
        if customer_name:
            requests.post(
                f"{TICKET_BASE_URL}/api/tickets/{ticket['id']}/update",
                json={
                    "text": f"Ticket opened by {customer_name}: {issue_description}",
                    "engineer": customer_name,
                    "source": "customer",
                },
                timeout=10
            )

        return {
            "Incident ID": ticket["id"],
            "Status": ticket["status"],
            "Device IP": ticket["device_ip"],
            "Priority": ticket["priority"],
            "Issue Description": ticket["description"],
            "Message": (
                f"Your incident has been logged as {ticket['id']}. "
                "The NOC team has been notified and an engineer will pick it up shortly. "
                "You can ask for an update or add more information at any time."
            )
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the ticketing system. Please try again shortly."}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_ticket_update(incident_id: str) -> dict:
    """
    Retrieves the current status and the LATEST ENGINEER UPDATE for a customer's ticket.

    Use this when the customer asks things like:
    - "What's the update on my ticket?"
    - "Any news on INC000001?"
    - "Has the engineer responded yet?"
    - "What's happening with my case?"
    - "Is my issue resolved?"

    INSTRUCTIONS FOR AI:
    - Always present the latest engineer update clearly and in plain language.
    - If the status is 'resolved' or 'closed', congratulate the customer and confirm.
    - If there are no engineer updates yet, tell the customer it's still being picked up.
    - Do NOT expose raw timestamps or internal fields — summarize naturally.

    'incident_id': e.g. INC000001
    """
    try:
        response = requests.get(f"{TICKET_BASE_URL}/api/tickets/{incident_id}", timeout=10)
        if response.status_code == 404:
            return {"error": f"Ticket {incident_id} was not found. Please check the incident number."}
        ticket = response.json()

        all_updates = ticket.get("updates", [])
        engineer_updates = [u for u in all_updates if u.get("source") != "customer"]
        latest_engineer = engineer_updates[-1] if engineer_updates else None

        return {
            "Incident ID": ticket["id"],
            "Current Status": ticket["status"],
            "Issue Description": ticket["description"],
            "Device IP": ticket["device_ip"],
            "Priority": ticket["priority"],
            "Assigned Engineer": ticket.get("assigned_engineer") or "Being assigned",
            "Opened At": ticket["created_at"],
            "Last Updated": ticket.get("updated_at") or "Awaiting first update",
            "Engineer Updates Count": len(engineer_updates),
            "Latest Engineer Update": {
                "From": latest_engineer.get("engineer") or "Engineer",
                "Time": latest_engineer["timestamp"],
                "Message": latest_engineer["text"],
                "Status Change": latest_engineer.get("status_change"),
            } if latest_engineer else None,
            "Note": "No engineer update yet — the NOC team has been notified and will respond shortly." if not latest_engineer else None,
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the ticketing system. Please try again shortly."}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_customer_info(
    incident_id: str,
    additional_info: str,
    customer_name: str = ""
) -> dict:
    """
    Adds additional information from the CUSTOMER to an existing open ticket.
    This message is immediately visible to the engineer handling the case.

    Use this when the customer wants to:
    - Add more details about their issue
    - Report that a problem is still ongoing after an engineer update
    - Confirm that an issue has been resolved from their side
    - Provide extra context (e.g., affected sites, time the issue started, logs)
    - Ask the engineer a follow-up question

    Example customer phrases that should trigger this:
    - "I want to add that the issue also affects site B"
    - "Tell the engineer the SIP trunk is still down after the reboot"
    - "Please inform them this started after the maintenance window at 02:00"
    - "The issue seems resolved on our end, thank you"

    INSTRUCTIONS FOR AI:
    - Use the customer's own words in 'additional_info' — do not rewrite them heavily.
    - If 'customer_name' is known from context, pass it in.
    - After posting, confirm to the customer that the engineer will see this immediately.

    'incident_id': e.g. INC000001
    'additional_info': the customer's message
    'customer_name': optional contact name
    """
    payload = {
        "text": additional_info,
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
            return {"error": f"Ticket {incident_id} was not found. Please check the incident number."}
        ticket = response.json()
        return {
            "Incident ID": ticket["id"],
            "Current Status": ticket["status"],
            "Your Message": additional_info,
            "Posted By": customer_name or "Customer",
            "Timestamp": ticket["updated_at"],
            "Message": (
                f"Your information has been added to {incident_id}. "
                "The engineer handling your case will see it immediately on their screen."
            )
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the ticketing system. Please try again shortly."}
    except Exception as e:
        return {"error": str(e)}
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


# ─── Device tools (unchanged) ─────────────────────────────────────────────────

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


# ─── CUSTOMER-FACING Ticketing Tools ──────────────────────────────────────────
#
# IMPORTANT DESIGN RULE:
#   - These tools are for CUSTOMERS talking to the Foundry agent ONLY.
#   - Engineers do NOT use MCP. Engineers work exclusively in the Flask GUI.
#   - Customers can: open tickets, retrieve engineer updates, add info to a ticket.
#   - Customers CANNOT change ticket status — only the engineer can via the GUI.
#
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def Open_CriticalTicket(
    admin_ip: str,
    issue_description: str,
    priority: str = "critical",
    customer_name: str = ""
) -> dict:
    """
    Opens a new incident ticket on behalf of the CUSTOMER.

    INSTRUCTIONS FOR AI:
    - 'admin_ip': use the 'Admin IP address' from search_equipment. Never use Host IP.
    - 'issue_description': summarize the problem the customer described.
      If unclear, ask the customer to describe it before calling this.
    - 'priority': one of 'critical', 'high', 'medium', 'low'. Default 'critical'.
    - 'customer_name': name of the customer contact if known.

    After opening, tell the customer their Incident ID and that they can:
    - Ask for updates at any time ("what's the status of INC000001?")
    - Add more information ("I want to add that...")
    The NOC engineer will be notified and handle the case from their desk.
    """
    payload = {
        "device_ip": admin_ip,
        "description": issue_description,
        "priority": priority,
        "assigned_engineer": None,
    }
    try:
        response = requests.post(f"{TICKET_BASE_URL}/api/tickets", json=payload, timeout=10)
        ticket = response.json()

        # Log the opening as a customer entry in the activity log
        if customer_name:
            requests.post(
                f"{TICKET_BASE_URL}/api/tickets/{ticket['id']}/update",
                json={
                    "text": f"Ticket opened by {customer_name}: {issue_description}",
                    "engineer": customer_name,
                    "source": "customer",
                },
                timeout=10
            )

        return {
            "Incident ID": ticket["id"],
            "Status": ticket["status"],
            "Device IP": ticket["device_ip"],
            "Priority": ticket["priority"],
            "Issue Description": ticket["description"],
            "Message": (
                f"Your incident has been logged as {ticket['id']}. "
                "The NOC team has been notified and an engineer will pick it up shortly. "
                "You can ask for an update or add more information at any time."
            )
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the ticketing system. Please try again shortly."}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_ticket_update(incident_id: str) -> dict:
    """
    Retrieves the current status and the LATEST ENGINEER UPDATE for a customer's ticket.

    Use this when the customer asks things like:
    - "What's the update on my ticket?"
    - "Any news on INC000001?"
    - "Has the engineer responded yet?"
    - "What's happening with my case?"
    - "Is my issue resolved?"

    INSTRUCTIONS FOR AI:
    - Always present the latest engineer update clearly and in plain language.
    - If the status is 'resolved' or 'closed', congratulate the customer and confirm.
    - If there are no engineer updates yet, tell the customer it's still being picked up.
    - Do NOT expose raw timestamps or internal fields — summarize naturally.

    'incident_id': e.g. INC000001
    """
    try:
        response = requests.get(f"{TICKET_BASE_URL}/api/tickets/{incident_id}", timeout=10)
        if response.status_code == 404:
            return {"error": f"Ticket {incident_id} was not found. Please check the incident number."}
        ticket = response.json()

        all_updates = ticket.get("updates", [])
        engineer_updates = [u for u in all_updates if u.get("source") != "customer"]
        latest_engineer = engineer_updates[-1] if engineer_updates else None

        return {
            "Incident ID": ticket["id"],
            "Current Status": ticket["status"],
            "Issue Description": ticket["description"],
            "Device IP": ticket["device_ip"],
            "Priority": ticket["priority"],
            "Assigned Engineer": ticket.get("assigned_engineer") or "Being assigned",
            "Opened At": ticket["created_at"],
            "Last Updated": ticket.get("updated_at") or "Awaiting first update",
            "Engineer Updates Count": len(engineer_updates),
            "Latest Engineer Update": {
                "From": latest_engineer.get("engineer") or "Engineer",
                "Time": latest_engineer["timestamp"],
                "Message": latest_engineer["text"],
                "Status Change": latest_engineer.get("status_change"),
            } if latest_engineer else None,
            "Note": "No engineer update yet — the NOC team has been notified and will respond shortly." if not latest_engineer else None,
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the ticketing system. Please try again shortly."}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_customer_info(
    incident_id: str,
    additional_info: str,
    customer_name: str = ""
) -> dict:
    """
    Adds additional information from the CUSTOMER to an existing open ticket.
    This message is immediately visible to the engineer handling the case.

    Use this when the customer wants to:
    - Add more details about their issue
    - Report that a problem is still ongoing after an engineer update
    - Confirm that an issue has been resolved from their side
    - Provide extra context (e.g., affected sites, time the issue started, logs)
    - Ask the engineer a follow-up question

    Example customer phrases that should trigger this:
    - "I want to add that the issue also affects site B"
    - "Tell the engineer the SIP trunk is still down after the reboot"
    - "Please inform them this started after the maintenance window at 02:00"
    - "The issue seems resolved on our end, thank you"

    INSTRUCTIONS FOR AI:
    - Use the customer's own words in 'additional_info' — do not rewrite them heavily.
    - If 'customer_name' is known from context, pass it in.
    - After posting, confirm to the customer that the engineer will see this immediately.

    'incident_id': e.g. INC000001
    'additional_info': the customer's message
    'customer_name': optional contact name
    """
    payload = {
        "text": additional_info,
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
            return {"error": f"Ticket {incident_id} was not found. Please check the incident number."}
        ticket = response.json()
        return {
            "Incident ID": ticket["id"],
            "Current Status": ticket["status"],
            "Your Message": additional_info,
            "Posted By": customer_name or "Customer",
            "Timestamp": ticket["updated_at"],
            "Message": (
                f"Your information has been added to {incident_id}. "
                "The engineer handling your case will see it immediately on their screen."
            )
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach the ticketing system. Please try again shortly."}
    except Exception as e:
        return {"error": str(e)}
