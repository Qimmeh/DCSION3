"""
Activity Taxonomy & 5-Dimensional Base Stat Vectors
===================================================
Defines canonical categories, activity types, and default points/hour rates
across Academic, Work, Social, Health, and Errands.
"""

FIVE_STATS = ["academic", "work", "social", "health", "errands"]

# Standard rates (points per hour)
BASE_STAT_TAXONOMY = {
    # --- Academic ---
    "lecture": {"academic": 10.0, "work": 0.0, "social": 1.0, "health": 2.0, "errands": 0.0},
    "tutorial": {"academic": 9.0, "work": 0.0, "social": 2.0, "health": 2.0, "errands": 0.0},
    "lab": {"academic": 10.0, "work": 0.0, "social": 2.0, "health": 3.0, "errands": 0.0},
    "seminar": {"academic": 8.0, "work": 0.0, "social": 4.0, "health": 2.0, "errands": 0.0},
    "exam": {"academic": 15.0, "work": 0.0, "social": 1.0, "health": 5.0, "errands": 0.0},
    "quiz": {"academic": 12.0, "work": 0.0, "social": 0.0, "health": 3.0, "errands": 0.0},
    "revision": {"academic": 12.0, "work": 0.0, "social": 0.0, "health": 3.0, "errands": 0.0},
    "coding_assignment": {"academic": 10.0, "work": 0.0, "social": 0.0, "health": 2.0, "errands": 0.0},
    "essay": {"academic": 11.0, "work": 0.0, "social": 0.0, "health": 2.0, "errands": 0.0},
    "group_project": {"academic": 7.0, "work": 0.0, "social": 8.0, "health": 2.0, "errands": 0.0},
    "presentation": {"academic": 12.0, "work": 0.0, "social": 6.0, "health": 4.0, "errands": 0.0},

    # --- Work ---
    "part_time_shift": {"academic": 0.0, "work": 10.0, "social": 5.0, "health": 7.0, "errands": 0.0},
    "full_time_shift": {"academic": 0.0, "work": 12.0, "social": 4.0, "health": 8.0, "errands": 0.0},
    "freelance": {"academic": 2.0, "work": 10.0, "social": 1.0, "health": 3.0, "errands": 0.0},
    "client_meeting": {"academic": 2.0, "work": 8.0, "social": 7.0, "health": 2.0, "errands": 0.0},
    "gig_work": {"academic": 0.0, "work": 9.0, "social": 2.0, "health": 8.0, "errands": 2.0},

    # --- Social ---
    "friends": {"academic": 0.0, "work": 0.0, "social": 6.0, "health": 1.0, "errands": 0.0},
    "family": {"academic": 0.0, "work": 0.0, "social": 5.0, "health": 1.0, "errands": 0.0},
    "dating": {"academic": 0.0, "work": 0.0, "social": 6.0, "health": 1.0, "errands": 0.0},
    "club_event": {"academic": 0.0, "work": 0.0, "social": 9.0, "health": 3.0, "errands": 0.0},
    "party": {"academic": 0.0, "work": 0.0, "social": 10.0, "health": 5.0, "errands": 0.0},

    # --- Health & Physical Strain ---
    "gym": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 7.0, "errands": 0.0},
    "running": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 8.0, "errands": 0.0},
    "sports": {"academic": 0.0, "work": 0.0, "social": 4.0, "health": 8.0, "errands": 0.0},

    # --- Recovery (Negative Load Credits) ---
    "sleep": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": -12.0, "errands": 0.0},
    "nap": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": -7.0, "errands": 0.0},
    "rest": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": -5.0, "errands": 0.0},
    "meal": {"academic": 0.0, "work": 0.0, "social": 2.0, "health": -4.0, "errands": 0.0},
    "walk": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": -4.0, "errands": 0.0},

    # --- Errands ---
    "groceries": {"academic": 0.0, "work": 0.0, "social": 1.0, "health": 3.0, "errands": 10.0},
    "banking": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 1.0, "errands": 8.0},
    "printing": {"academic": 2.0, "work": 0.0, "social": 0.0, "health": 1.0, "errands": 8.0},
    "parcel": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 2.0, "errands": 7.0},
    "pharmacy": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 1.0, "errands": 8.0},
    "laundry": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 3.0, "errands": 7.0},
}

DEFAULT_CATEGORY_FALLBACK = {
    "academic": {"academic": 10.0, "work": 0.0, "social": 0.0, "health": 2.0, "errands": 0.0},
    "work": {"academic": 0.0, "work": 10.0, "social": 2.0, "health": 4.0, "errands": 0.0},
    "social": {"academic": 0.0, "work": 0.0, "social": 7.0, "health": 1.0, "errands": 0.0},
    "health": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 6.0, "errands": 0.0},
    "errands": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 2.0, "errands": 8.0},
    "recovery": {"academic": 0.0, "work": 0.0, "social": 0.0, "health": -6.0, "errands": 0.0},
    "other": {"academic": 1.0, "work": 1.0, "social": 1.0, "health": 1.0, "errands": 1.0},
}


def get_default_stat_vector(activity_type: str = None, category: str = None) -> dict:
    """
    Returns default 5-stat base rates based on specific activity_type or high-level category.
    """
    if activity_type:
        key = activity_type.lower().strip().replace(" ", "_")
        if key in BASE_STAT_TAXONOMY:
            return dict(BASE_STAT_TAXONOMY[key])

    if category:
        cat_key = category.lower().strip()
        if cat_key in DEFAULT_CATEGORY_FALLBACK:
            return dict(DEFAULT_CATEGORY_FALLBACK[cat_key])

    return {"academic": 5.0, "work": 0.0, "social": 0.0, "health": 1.0, "errands": 0.0}
