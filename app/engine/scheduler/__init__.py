"""
Smart Todo & Timeline Scheduler Engine Package
==============================================
Provides deadline collision detection, task splitting, candidate generation,
and sacrifice-cost optimization adhering to "Finish Before" principles.
"""
from app.engine.scheduler.collision import detect_deadline_collisions
from app.engine.scheduler.splitter import split_task_into_blocks
from app.engine.scheduler.optimizer import (
    generate_smart_timeline,
    find_available_slots_on_day,
    SACRIFICE_COSTS,
)

__all__ = [
    "detect_deadline_collisions",
    "split_task_into_blocks",
    "generate_smart_timeline",
    "find_available_slots_on_day",
    "SACRIFICE_COSTS",
]
