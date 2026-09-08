"""
Task Splitting & Work Decomposition Engine
==========================================
Divides large, splittable tasks into optimal, cognitively manageable blocks
bounded by minimum_block_minutes and maximum_block_minutes.
Avoids creating meaningless micro-fragments or exhausting marathons.
"""
from typing import List, Dict, Any

PHASE_NAMES = [
    "Phase 1: Research & Outline",
    "Phase 2: Core Draft / Implementation",
    "Phase 3: Deep Work & Revision",
    "Phase 4: Testing & Final Polish",
    "Phase 5: Final Review",
]


def split_task_into_blocks(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Decomposes a task into structured session blocks.
    Example: 8h (480 min) programming assignment ->
      [120 min Phase 1, 150 min Phase 2, 120 min Phase 3, 90 min Phase 4]
    """
    total_minutes = task.get("remaining_effort_minutes") or task.get("duration_minutes") or 60
    splittable = task.get("splittable", True)
    min_block = max(30, task.get("minimum_block_minutes", 30))
    max_block = max(min_block, task.get("maximum_block_minutes", 180))

    if not splittable or total_minutes <= max_block:
        return [{
            "task_id": task.get("id"),
            "title": task.get("title", "Task"),
            "duration_minutes": total_minutes,
            "phase_index": 1,
            "phase_name": "Full Session",
            "category": task.get("category", "Academic"),
            "intensity": task.get("intensity", "Medium"),
            "priority": task.get("priority", "Medium"),
        }]

    # Decompose into chunks
    remaining = total_minutes
    blocks = []
    phase_idx = 0

    while remaining > 0:
        if remaining <= max_block:
            chunk = remaining
            remaining = 0
        else:
            # Prefer 90 to 120 minute sessions when possible
            chunk = min(max_block, max(min_block, 120))
            if remaining - chunk < min_block:
                # Avoid leaving a dangling fragment smaller than min_block
                chunk = remaining // 2
            remaining -= chunk

        phase_title = PHASE_NAMES[phase_idx] if phase_idx < len(PHASE_NAMES) else f"Phase {phase_idx + 1}"
        blocks.append({
            "task_id": task.get("id"),
            "title": f"{task.get('title', 'Task')} ({phase_title})",
            "duration_minutes": chunk,
            "phase_index": phase_idx + 1,
            "phase_name": phase_title,
            "category": task.get("category", "Academic"),
            "intensity": task.get("intensity", "Medium"),
            "priority": task.get("priority", "Medium"),
        })
        phase_idx += 1

    return blocks
