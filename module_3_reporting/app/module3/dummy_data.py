# dummy_data.py

from datetime import date, timedelta

# ==================================================
# SIMULATED USERS (FOR ROLE-BASED VIEWS)
# ==================================================

USERS = {
    1: {"name": "Homeowner A", "unit": "A-10-1", "role": "Homeowner"},
    2: {"name": "Homeowner B", "unit": "B-05-2", "role": "Homeowner"},
    3: {"name": "Homeowner C", "unit": "C-01-5", "role": "Homeowner"},
    4: {"name": "Homeowner D", "unit": "D-12-8", "role": "Homeowner"}
}

SIMULATED_LOGIN_USER_ID = 1  # change to test different homeowners


# ==================================================
# FULL MOCK DEFECT DATA (SYSTEM-WIDE)
# ==================================================

all_defects_data = [
    {
        "id": 101,
        "unit": "A-10-1",
        "desc": "Wall crack in master bedroom",
        "status": "Pending",
        "owner_id": 1,
        "urgency": "High",
        "deadline": (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
        "is_overdue": False,
        "hda_compliant": False,
        "remarks": "Crack widening slightly over time"
    },
    {
        "id": 102,
        "unit": "B-05-2",
        "desc": "Leaking pipe under kitchen sink",
        "status": "In Progress",
        "owner_id": 2,
        "urgency": "High",
        "deadline": (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "is_overdue": True,
        "hda_compliant": False,
        "remarks": "Temporary fix applied, replacement pending"
    },
    {
        "id": 103,
        "unit": "A-10-1",
        "desc": "Broken tile in bathroom",
        "status": "Completed",
        "owner_id": 1,
        "urgency": "Low",
        "deadline": (date.today() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "is_overdue": False,
        "hda_compliant": True,
        "remarks": "Tile replaced successfully"
    },
    {
        "id": 104,
        "unit": "C-01-5",
        "desc": "Faulty electrical wiring in living room",
        "status": "Delayed",
        "owner_id": 3,
        "urgency": "High",
        "deadline": (date.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "is_overdue": True,
        "hda_compliant": False,
        "remarks": "Contractor unavailable, rescheduled"
    },
    {
        "id": 105,
        "unit": "B-05-2",
        "desc": "Balcony sliding door stuck",
        "status": "Completed",
        "owner_id": 2,
        "urgency": "Low",
        "deadline": (date.today() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "is_overdue": False,
        "hda_compliant": True,
        "remarks": "Roller mechanism adjusted"
    },
    {
        "id": 106,
        "unit": "D-12-8",
        "desc": "Ceiling water stain near air-conditioner",
        "status": "Pending",
        "owner_id": 4,
        "urgency": "High",
        "deadline": (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "is_overdue": False,
        "hda_compliant": False,
        "remarks": "Inspection scheduled"
    }
]


# ==================================================
# ROLE-BASED DATA ACCESS
# ==================================================

def get_defects_for_role(role):
    """
    Homeowner  → sees only own unit defects
    Developer  → sees all defects
    Legal      → sees all defects (read-only)
    """
    if role == "Homeowner":
        return [
            d for d in all_defects_data
            if d["owner_id"] == SIMULATED_LOGIN_USER_ID
        ]

    # Developer & Legal
    return all_defects_data


# ==================================================
# DASHBOARD STATISTICS (DYNAMIC)
# ==================================================

def calculate_stats(defects):
    return {
        "total": len(defects),
        "pending": len([
            d for d in defects
            if d["status"] in ["Pending", "In Progress", "Delayed"]
        ]),
        "completed": len([
            d for d in defects
            if d["status"] == "Completed"
        ]),
        "critical": len([
            d for d in defects
            if d["urgency"] == "High" and not d["hda_compliant"]
        ])
    }
