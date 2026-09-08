"""
Ambient Workload Manager - Core Database Models
================================================
Comprehensive, flexible, and production-grade SQLAlchemy ORM models
for PostgreSQL supporting the Five-Dimensional Capacity Architecture:
  - Academic
  - Work
  - Social
  - Health
  - Errands

Architecture adheres to:
  - Deterministic scoring engine separation
  - AI Ghost Schedules & confirmation safeguards
  - Domino Rebalancer & Capacity Simulator workflows
  - Smart Errand Clustering & Protected Recovery Windows
"""

from datetime import datetime, date, time
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


# ============================================================================
# 1. USER & PERSONALIZATION LAYER
# ============================================================================

class User(UserMixin, db.Model):
    """
    Primary user entity for authentication, ownership, and relationship anchoring.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 1-to-1 Profile
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')

    # Schedules & Timetables
    schedules = db.relationship('Schedule', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Activities, Tasks & Scored Events
    activities = db.relationship('Activity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    workload_events = db.relationship('WorkloadEvent', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    workload_snapshots = db.relationship('WorkloadSnapshot', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Battery & Recovery Subsystem
    battery_snapshots = db.relationship('BatterySnapshot', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    recovery_records = db.relationship('RecoveryRecord', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Smart Scheduler & Recommendations
    recommendations = db.relationship('Recommendation', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    activity_dependencies = db.relationship('ActivityDependency', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Capacity Simulator & Ghost Schedules
    commitments = db.relationship('Commitment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    ghost_changes = db.relationship('GhostChange', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    recovery_windows = db.relationship('RecoveryWindow', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Errand & Location System
    locations = db.relationship('Location', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    errand_clusters = db.relationship('ErrandCluster', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Documents & AI Parsing
    uploaded_documents = db.relationship('UploadedDocument', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Notifications & Audit
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notification_pref = db.relationship('NotificationPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Profile(db.Model):
    """
    User capacity thresholds, intervention preferences, and learned personalization parameters.
    """
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)

    # Capacity Baselines (UX threshold percentages: 0 - 100)
    target_daily_capacity = db.Column(db.Float, default=80.0)
    target_weekly_capacity = db.Column(db.Float, default=85.0)

    # Study and Day Boundaries
    preferred_study_start = db.Column(db.Time, default=time(9, 0))
    preferred_study_end = db.Column(db.Time, default=time(21, 0))
    typical_commute_minutes = db.Column(db.Integer, default=30)

    # Sleep & Recovery Configuration (Sections 4.3, 6.10, 7.6)
    target_sleep_hours = db.Column(db.Float, default=8.0) # Configurable baseline 6-10 h
    minimum_sleep_hours = db.Column(db.Float, default=6.0) # Protected non-negotiable floor
    preferred_sleep_start = db.Column(db.Time, default=time(23, 0))
    preferred_sleep_end = db.Column(db.Time, default=time(7, 0))

    # Learned Personalization Parameters
    task_extension_rate = db.Column(db.Float, default=1.0) # e.g. 1.8x if coding usually runs long
    intervention_style = db.Column(db.String(20), default='balanced') # 'gentle', 'balanced', 'strict'
    assumed_complete_enabled = db.Column(db.Boolean, default=True)
    suppress_notifications_during_recovery = db.Column(db.Boolean, default=True)

    # Customizable Dimension Weights (Defaults: Academic=25%, Work=20%, Social=15%, Health=25%, Errands=15%)
    dimension_weights = db.Column(db.JSON, default=lambda: {
        "academic": 0.25,
        "work": 0.20,
        "social": 0.15,
        "health": 0.25,
        "errands": 0.15
    })

    # Historical Learned Modifiers (per category / activity type)
    personal_modifiers = db.Column(db.JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_daily_capacity": self.target_daily_capacity,
            "target_weekly_capacity": self.target_weekly_capacity,
            "preferred_study_start": self.preferred_study_start.strftime("%H:%M") if self.preferred_study_start else None,
            "preferred_study_end": self.preferred_study_end.strftime("%H:%M") if self.preferred_study_end else None,
            "typical_commute_minutes": self.typical_commute_minutes,
            "target_sleep_hours": self.target_sleep_hours,
            "minimum_sleep_hours": self.minimum_sleep_hours,
            "preferred_sleep_start": self.preferred_sleep_start.strftime("%H:%M") if self.preferred_sleep_start else None,
            "preferred_sleep_end": self.preferred_sleep_end.strftime("%H:%M") if self.preferred_sleep_end else None,
            "task_extension_rate": self.task_extension_rate,
            "intervention_style": self.intervention_style,
            "assumed_complete_enabled": self.assumed_complete_enabled,
            "suppress_notifications_during_recovery": self.suppress_notifications_during_recovery,
            "dimension_weights": self.dimension_weights or {},
            "personal_modifiers": self.personal_modifiers or {}
        }


# ============================================================================
# 2. TIMETABLE & RECURRING SCHEDULE SYSTEM
# ============================================================================

class Schedule(db.Model):
    """
    Named timetable container (e.g., 'Semester 1 2026', 'Finals Period').
    """
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(50))
    academic_year = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True, index=True)
    valid_from = db.Column(db.Date)
    valid_until = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recurrences = db.relationship('ScheduleRecurrence', backref='schedule', lazy='dynamic', cascade='all, delete-orphan')
    events = db.relationship('ScheduleEvent', backref='schedule', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "is_active": self.is_active,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


class ScheduleRecurrence(db.Model):
    """
    Recurring rules extracted from university timetables (e.g., Every Monday 10:00-12:00).
    """
    __tablename__ = 'schedule_recurrences'

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id', ondelete='CASCADE'), nullable=False)
    course_code = db.Column(db.String(50), index=True)
    course_name = db.Column(db.String(150), nullable=False)
    event_type = db.Column(db.String(50), default='lecture') # lecture, tutorial, lab, seminar, exam
    day_of_week = db.Column(db.Integer, nullable=False) # 0=Monday ... 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(150))
    is_fixed = db.Column(db.Boolean, default=True) # Cannot be casually moved by rebalancer
    confidence_score = db.Column(db.Float, default=1.0) # VLM parser confidence
    raw_metadata = db.Column(db.JSON, default=dict)

    events = db.relationship('ScheduleEvent', backref='recurrence', lazy='dynamic')

    def to_dict(self):
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "event_type": self.event_type,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "location": self.location,
            "is_fixed": self.is_fixed,
            "confidence_score": self.confidence_score
        }


class ScheduleEvent(db.Model):
    """
    Concrete or generated timetable instances linked to dates and recurrences.
    """
    __tablename__ = 'schedule_events'

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id', ondelete='CASCADE'), nullable=False)
    recurrence_id = db.Column(db.Integer, db.ForeignKey('schedule_recurrences.id', ondelete='SET NULL'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), index=True)

    title = db.Column(db.String(150), nullable=False)
    event_type = db.Column(db.String(50))
    day_of_week = db.Column(db.Integer)
    date = db.Column(db.Date, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(150))
    is_fixed = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(30), default='active') # active, cancelled, rescheduled

    # Linked Activity if converted for scoring
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='SET NULL'))

    def to_dict(self):
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "recurrence_id": self.recurrence_id,
            "title": self.title,
            "event_type": self.event_type,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "location": self.location,
            "is_fixed": self.is_fixed,
            "status": self.status,
            "activity_id": self.activity_id
        }


# ============================================================================
# 3. ACTIVITY & WORKLOAD SCORING ENGINE
# ============================================================================

class Activity(db.Model):
    """
    Central life block / task entity consumed by the deterministic workload engine.
    Supports multi-dimensional stat vectors and recovery classification.
    """
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    schedule_event_id = db.Column(db.Integer, db.ForeignKey('schedule_events.id', ondelete='SET NULL'))
    parent_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE')) # Subtask hierarchy

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)

    # Primary Taxonomy: Academic, Work, Social, Health, Errands, Other
    category = db.Column(db.String(50), nullable=False, index=True)
    activity_type = db.Column(db.String(80), index=True) # e.g. lecture, coding_assignment, part_time_shift, sleep

    # The 5-Dimensional Base Stat Vector (points/hour contributions)
    # Default format: {"academic": 10, "work": 0, "social": 0, "health": 2, "errands": 0}
    stat_vector = db.Column(db.JSON, nullable=False, default=lambda: {
        "academic": 0.0,
        "work": 0.0,
        "social": 0.0,
        "health": 0.0,
        "errands": 0.0
    })

    # Temporal & Scheduling Coordinates
    start_time = db.Column(db.DateTime, index=True)
    end_time = db.Column(db.DateTime, index=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    continuous_minutes = db.Column(db.Integer, default=60) # For continuity modifier calculation

    # Modifiers & Constraints
    intensity = db.Column(db.String(20), default='Medium') # Low (0.6x), Medium (1.0x), High (1.35x), Extreme (1.7x)
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High, Critical
    is_fixed = db.Column(db.Boolean, default=False) # True for exams/lectures; False for flexible study
    deadline = db.Column(db.DateTime, index=True)

    # Smart Todo & Timeline Scheduler Attributes (Section 6.2)
    estimated_effort_minutes = db.Column(db.Integer, default=60)
    remaining_effort_minutes = db.Column(db.Integer, default=60)
    minimum_block_minutes = db.Column(db.Integer, default=30)
    maximum_block_minutes = db.Column(db.Integer, default=180)
    splittable = db.Column(db.Boolean, default=True)
    flexibility = db.Column(db.String(20), default='movable') # fixed, movable, shortenable, cancelable
    consequence_cost = db.Column(db.Float, default=2.0) # 1.0 (very low) to 10.0 (extreme/prohibited)
    recommended_finish_date = db.Column(db.DateTime)
    preferred_windows = db.Column(db.JSON, default=list) # e.g. ["morning", "afternoon"]
    safety_buffer_minutes = db.Column(db.Integer, default=60)

    # Location & Friction
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id', ondelete='SET NULL'))
    location_name = db.Column(db.String(150))
    travel_time_minutes = db.Column(db.Integer, default=0)

    # Optimization Flags
    is_recurring = db.Column(db.Boolean, default=False)
    is_clusterable = db.Column(db.Boolean, default=False) # Eligible for Errand Clustering
    recovery_type = db.Column(db.String(50)) # sleep, nap, rest, meal, walk, social_disconnect

    # Status & Assumed-Complete Lifecycle
    status = db.Column(db.String(30), default='planned', index=True) # planned, in_progress, completed, skipped, extended, rescheduled
    confidence = db.Column(db.Float, default=1.0) # AI extraction confidence
    assumed_complete_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subtasks = db.relationship('Activity', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    workload_events = db.relationship('WorkloadEvent', backref='activity', lazy='dynamic', cascade='all, delete-orphan')
    errand_detail = db.relationship('ErrandDetail', backref='activity', uselist=False, cascade='all, delete-orphan')
    dependencies_out = db.relationship('ActivityDependency', foreign_keys='ActivityDependency.predecessor_id', backref='predecessor', lazy='dynamic', cascade='all, delete-orphan')
    dependencies_in = db.relationship('ActivityDependency', foreign_keys='ActivityDependency.successor_id', backref='successor', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_activity_user_dates', 'user_id', 'start_time', 'end_time'),
        db.Index('idx_activity_user_status', 'user_id', 'status'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "activity_type": self.activity_type,
            "stat_vector": self.stat_vector or {},
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "continuous_minutes": self.continuous_minutes,
            "intensity": self.intensity,
            "priority": self.priority,
            "is_fixed": self.is_fixed,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "estimated_effort_minutes": self.estimated_effort_minutes,
            "remaining_effort_minutes": self.remaining_effort_minutes,
            "minimum_block_minutes": self.minimum_block_minutes,
            "maximum_block_minutes": self.maximum_block_minutes,
            "splittable": self.splittable,
            "flexibility": self.flexibility,
            "consequence_cost": self.consequence_cost,
            "recommended_finish_date": self.recommended_finish_date.isoformat() if self.recommended_finish_date else None,
            "preferred_windows": self.preferred_windows or [],
            "safety_buffer_minutes": self.safety_buffer_minutes,
            "location_name": self.location_name,
            "travel_time_minutes": self.travel_time_minutes,
            "is_clusterable": self.is_clusterable,
            "recovery_type": self.recovery_type,
            "status": self.status,
            "confidence": self.confidence,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class WorkloadEvent(db.Model):
    """
    Deterministic scoring record generated for an activity on a given date.
    Stores raw scores (unbounded for analytics) and display scores (bounded by cap, e.g. 40 pts).
    """
    __tablename__ = 'workload_events'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)

    # 5 Stats Output Scores
    academic_raw = db.Column(db.Float, default=0.0)
    academic_display = db.Column(db.Float, default=0.0)

    work_raw = db.Column(db.Float, default=0.0)
    work_display = db.Column(db.Float, default=0.0)

    social_raw = db.Column(db.Float, default=0.0)
    social_display = db.Column(db.Float, default=0.0)

    health_raw = db.Column(db.Float, default=0.0)
    health_display = db.Column(db.Float, default=0.0)

    errands_raw = db.Column(db.Float, default=0.0)
    errands_display = db.Column(db.Float, default=0.0)

    # Applied Modifiers Audit
    duration_multiplier = db.Column(db.Float, default=1.0)
    intensity_multiplier = db.Column(db.Float, default=1.0)
    continuity_modifier = db.Column(db.Float, default=1.0)
    timing_modifier = db.Column(db.Float, default=1.0)
    context_modifier = db.Column(db.Float, default=1.0)

    is_recovery = db.Column(db.Boolean, default=False)
    applied_cap = db.Column(db.Float, default=40.0)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_workload_event_user_date', 'user_id', 'date'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "scores": {
                "academic": {"raw": self.academic_raw, "display": self.academic_display},
                "work": {"raw": self.work_raw, "display": self.work_display},
                "social": {"raw": self.social_raw, "display": self.social_display},
                "health": {"raw": self.health_raw, "display": self.health_display},
                "errands": {"raw": self.errands_raw, "display": self.errands_display}
            },
            "modifiers": {
                "duration": self.duration_multiplier,
                "intensity": self.intensity_multiplier,
                "continuity": self.continuity_modifier,
                "timing": self.timing_modifier,
                "context": self.context_modifier
            },
            "is_recovery": self.is_recovery,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


class WorkloadSnapshot(db.Model):
    """
    Daily Spike Gauge & Weekly Burn Rate rolling states.
    Captures temporal concentration, compression, and recovery deficit.
    """
    __tablename__ = 'workload_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    snapshot_type = db.Column(db.String(20), default='daily') # 'daily', 'weekly'

    # Normalized 0 - 100 Pressure per Dimension
    academic_load = db.Column(db.Float, default=0.0)
    work_load = db.Column(db.Float, default=0.0)
    social_load = db.Column(db.Float, default=0.0)
    health_load = db.Column(db.Float, default=0.0)
    errands_load = db.Column(db.Float, default=0.0)

    # Overall Capacity Pressures
    overall_score = db.Column(db.Float, default=0.0) # clamped 0 - 100
    peak_penalty = db.Column(db.Float, default=0.0)
    compression_penalty = db.Column(db.Float, default=0.0)
    recovery_deficit_penalty = db.Column(db.Float, default=0.0)
    burn_rate = db.Column(db.Float, default=0.0) # Rolling weekly accumulation

    # UX Warning State
    status_level = db.Column(db.String(20), default='normal') # normal (0-70), elevated (70-85), high (85-90), critical (90+)
    limiting_factor = db.Column(db.String(50)) # e.g. 'Time', 'Academic', 'Health'
    raw_details = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_snapshot_user_type_date', 'user_id', 'snapshot_type', 'date'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "snapshot_type": self.snapshot_type,
            "dimension_loads": {
                "academic": self.academic_load,
                "work": self.work_load,
                "social": self.social_load,
                "health": self.health_load,
                "errands": self.errands_load
            },
            "overall_score": self.overall_score,
            "peak_penalty": self.peak_penalty,
            "compression_penalty": self.compression_penalty,
            "recovery_deficit_penalty": self.recovery_deficit_penalty,
            "burn_rate": self.burn_rate,
            "status_level": self.status_level,
            "limiting_factor": self.limiting_factor,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# 4. CAPACITY SIMULATOR & DOMINO REBALANCER
# ============================================================================

class Commitment(db.Model):
    """
    Commitments evaluated in the Capacity Simulator ('What happens if I accept this?').
    """
    __tablename__ = 'commitments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='Work')
    estimated_hours = db.Column(db.Float, nullable=False)
    proposed_start = db.Column(db.DateTime)
    proposed_end = db.Column(db.DateTime)
    intensity = db.Column(db.String(20), default='Medium')
    priority = db.Column(db.String(20), default='Medium')

    # Simulation Outcome
    simulated_weekly_load_before = db.Column(db.Float)
    simulated_weekly_load_after = db.Column(db.Float)
    simulation_verdict = db.Column(db.String(30)) # Accept, Decline, Accept_With_Rebalance
    displaced_summary = db.Column(db.JSON, default=dict) # {"displaced_sleep_hrs": 1.5, "lost_recovery_blocks": 1}

    status = db.Column(db.String(30), default='simulating') # simulating, accepted, declined, rebalanced
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "category": self.category,
            "estimated_hours": self.estimated_hours,
            "proposed_start": self.proposed_start.isoformat() if self.proposed_start else None,
            "proposed_end": self.proposed_end.isoformat() if self.proposed_end else None,
            "simulation": {
                "before": self.simulated_weekly_load_before,
                "after": self.simulated_weekly_load_after,
                "verdict": self.simulation_verdict,
                "displaced": self.displaced_summary or {}
            },
            "status": self.status
        }


class GhostChange(db.Model):
    """
    A Ghost Schedule proposal awaiting explicit user confirmation.
    Prevents AI or rebalancing suggestions from silently mutating the real calendar.
    """
    __tablename__ = 'ghost_changes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    source_type = db.Column(db.String(50), nullable=False) # timetable_import, conversational_nlp, domino_rebalance, extension
    description = db.Column(db.String(255), nullable=False)
    reason = db.Column(db.Text)
    confidence_score = db.Column(db.Float, default=1.0)

    status = db.Column(db.String(30), default='PENDING', index=True) # PENDING, CONFIRMED, REJECTED, EXPIRED
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    items = db.relationship('GhostChangeItem', backref='ghost_change', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_type": self.source_type,
            "description": self.description,
            "reason": self.reason,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "items": [item.to_dict() for item in self.items]
        }


class GhostChangeItem(db.Model):
    """
    Individual atomic operations inside a Ghost proposal (CREATE, MOVE, UPDATE, DELETE).
    """
    __tablename__ = 'ghost_change_items'

    id = db.Column(db.Integer, primary_key=True)
    ghost_change_id = db.Column(db.Integer, db.ForeignKey('ghost_changes.id', ondelete='CASCADE'), nullable=False)

    source_event_id = db.Column(db.Integer, db.ForeignKey('schedule_events.id', ondelete='SET NULL'))
    source_activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='SET NULL'))

    operation = db.Column(db.String(20), nullable=False) # CREATE, MOVE, UPDATE, DELETE
    old_start = db.Column(db.DateTime)
    old_end = db.Column(db.DateTime)
    new_start = db.Column(db.DateTime)
    new_end = db.Column(db.DateTime)
    payload = db.Column(db.JSON, default=dict) # Contains full activity fields for CREATE/UPDATE

    def to_dict(self):
        return {
            "id": self.id,
            "ghost_change_id": self.ghost_change_id,
            "operation": self.operation,
            "old_start": self.old_start.isoformat() if self.old_start else None,
            "old_end": self.old_end.isoformat() if self.old_end else None,
            "new_start": self.new_start.isoformat() if self.new_start else None,
            "new_end": self.new_end.isoformat() if self.new_end else None,
            "payload": self.payload or {}
        }


class ActivityDependency(db.Model):
    """
    Dependency relationship between activities/tasks (e.g. task B must start after task A finishes).
    """
    __tablename__ = 'activity_dependencies'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    predecessor_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False, index=True)
    successor_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False, index=True)
    dependency_type = db.Column(db.String(30), default='finish_to_start') # finish_to_start, start_to_start
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "predecessor_id": self.predecessor_id,
            "successor_id": self.successor_id,
            "dependency_type": self.dependency_type
        }


class Recommendation(db.Model):
    """
    Smart Timeline or Survival Plan recommendation awaiting user approval.
    """
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='rebalance') # timeline, survival_plan, rebalance, recovery
    summary = db.Column(db.Text)
    reasoning = db.Column(db.Text)

    # Optimization Metrics
    plan_score = db.Column(db.Float, default=0.0)
    sacrifice_cost = db.Column(db.Float, default=0.0)
    overload_reduction = db.Column(db.Float, default=0.0)

    status = db.Column(db.String(30), default='suggested', index=True) # suggested, accepted, rejected, modified
    feedback_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    actions = db.relationship('RecommendationAction', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "category": self.category,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "plan_score": self.plan_score,
            "sacrifice_cost": self.sacrifice_cost,
            "overload_reduction": self.overload_reduction,
            "status": self.status,
            "feedback_notes": self.feedback_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "actions": [a.to_dict() for a in self.actions]
        }


class RecommendationAction(db.Model):
    """
    Atomic scheduling step within a recommendation (e.g. MOVE, SHORTEN, SPLIT, ADD_RECOVERY).
    """
    __tablename__ = 'recommendation_actions'

    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendations.id', ondelete='CASCADE'), nullable=False, index=True)
    action_type = db.Column(db.String(30), nullable=False) # MOVE, SHORTEN, SPLIT, ADD_RECOVERY, PROTECT
    target_activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='SET NULL'))
    details = db.Column(db.JSON, default=dict)
    sacrifice_cost = db.Column(db.Float, default=0.0)

    target_activity = db.relationship('Activity')

    def to_dict(self):
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "action_type": self.action_type,
            "target_activity_id": self.target_activity_id,
            "details": self.details or {},
            "sacrifice_cost": self.sacrifice_cost
        }


# ============================================================================
# 5. RECOVERY PROTOCOL & ZERO-DISTURBANCE
# ============================================================================

class RecoveryWindow(db.Model):
    """
    Protected recovery slots created by the system to prevent burnout after high-load spikes.
    """
    __tablename__ = 'recovery_windows'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, nullable=False)

    recovery_type = db.Column(db.String(50), default='rest') # sleep, nap, rest, meal, outdoor_walk, disconnect
    is_protected = db.Column(db.Boolean, default=True) # Scheduler will preserve this window
    is_utilized = db.Column(db.Boolean, default=False)
    suppress_notifications = db.Column(db.Boolean, default=True)

    recommended_actions = db.Column(db.JSON, default=lambda: [
        "Get food outside", "Take a short walk", "Fully disconnect"
    ])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "recovery_type": self.recovery_type,
            "is_protected": self.is_protected,
            "is_utilized": self.is_utilized,
            "suppress_notifications": self.suppress_notifications,
            "recommended_actions": self.recommended_actions or []
        }


class RecoveryRecord(db.Model):
    """
    Daily sleep and recovery record tracking actual sleep vs target, deficit, and accumulated debt.
    """
    __tablename__ = 'recovery_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)

    actual_sleep_hours = db.Column(db.Float, default=8.0)
    target_sleep_hours = db.Column(db.Float, default=8.0)
    sleep_deficit_hours = db.Column(db.Float, default=0.0) # max(0, target - actual)
    recovery_debt_carried = db.Column(db.Float, default=0.0)
    naps_minutes = db.Column(db.Integer, default=0)
    recovery_activities_minutes = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(255))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_recovery_user_date'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "actual_sleep_hours": self.actual_sleep_hours,
            "target_sleep_hours": self.target_sleep_hours,
            "sleep_deficit_hours": self.sleep_deficit_hours,
            "recovery_debt_carried": self.recovery_debt_carried,
            "naps_minutes": self.naps_minutes,
            "recovery_activities_minutes": self.recovery_activities_minutes,
            "notes": self.notes,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None
        }


class BatterySnapshot(db.Model):
    """
    Daily snapshot of Battery State: starting capacity, drain, recovery, current and projected battery,
    capacity load, and UX state categorization.
    """
    __tablename__ = 'battery_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)

    start_battery = db.Column(db.Float, default=100.0)
    drain = db.Column(db.Float, default=0.0)
    recovery = db.Column(db.Float, default=0.0)
    fatigue_penalties = db.Column(db.Float, default=0.0)
    current_battery = db.Column(db.Float, default=100.0) # clamp(start - drain + recovery - fatigue, 0, 100)
    projected_battery = db.Column(db.Float, default=100.0)
    recovery_debt = db.Column(db.Float, default=0.0)
    capacity_load = db.Column(db.Float, default=0.0) # Workload / max(Battery, 10) * 100
    battery_state = db.Column(db.String(30), default='healthy') # healthy, reduced, low, very_low, critical
    details = db.Column(db.JSON, default=dict)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_battery_user_date'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "start_battery": self.start_battery,
            "drain": self.drain,
            "recovery": self.recovery,
            "fatigue_penalties": self.fatigue_penalties,
            "current_battery": self.current_battery,
            "projected_battery": self.projected_battery,
            "recovery_debt": self.recovery_debt,
            "capacity_load": self.capacity_load,
            "battery_state": self.battery_state,
            "details": self.details or {},
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }


# ============================================================================
# 6. SMART ERRAND & LOCATION OPTIMIZATION
# ============================================================================

class Location(db.Model):
    """
    Physical coordinates and travel anchors (supermarkets, campus, home, clinics).
    """
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='supermarket') # supermarket, bank, pharmacy, campus, home, gym
    address = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    opening_time = db.Column(db.Time)
    closing_time = db.Column(db.Time)
    typical_travel_minutes = db.Column(db.Integer, default=15)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "opening_time": self.opening_time.strftime("%H:%M") if self.opening_time else None,
            "closing_time": self.closing_time.strftime("%H:%M") if self.closing_time else None,
            "typical_travel_minutes": self.typical_travel_minutes
        }


class ErrandCluster(db.Model):
    """
    Consolidated errand blocks combining multiple errands to reduce travel time and fragmentation.
    """
    __tablename__ = 'errand_clusters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False) # e.g. "Saturday Afternoon Errand Run"
    scheduled_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)

    total_duration_minutes = db.Column(db.Integer)
    saved_travel_minutes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='suggested') # suggested, confirmed, completed, cancelled
    route_order = db.Column(db.JSON, default=list) # Ordered sequence of Activity IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    errands = db.relationship('ErrandDetail', backref='cluster', lazy='dynamic')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "total_duration_minutes": self.total_duration_minutes,
            "saved_travel_minutes": self.saved_travel_minutes,
            "status": self.status,
            "route_order": self.route_order or []
        }


class ErrandDetail(db.Model):
    """
    Specialized errand metadata linked 1-to-1 with an Activity of category 'Errands'.
    """
    __tablename__ = 'errand_details'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), unique=True, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id', ondelete='SET NULL'))
    cluster_id = db.Column(db.Integer, db.ForeignKey('errand_clusters.id', ondelete='SET NULL'))

    errand_subtype = db.Column(db.String(50)) # groceries, parcel, pharmacy, banking, laundry, printing
    estimated_errand_minutes = db.Column(db.Integer, default=30)
    travel_time_minutes = db.Column(db.Integer, default=15)
    physical_intensity = db.Column(db.String(20), default='Medium')
    preferred_window = db.Column(db.String(50), default='after_class') # morning, after_class, weekend
    is_clustered = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "location_id": self.location_id,
            "cluster_id": self.cluster_id,
            "errand_subtype": self.errand_subtype,
            "estimated_errand_minutes": self.estimated_errand_minutes,
            "travel_time_minutes": self.travel_time_minutes,
            "physical_intensity": self.physical_intensity,
            "preferred_window": self.preferred_window,
            "is_clustered": self.is_clustered
        }


# ============================================================================
# 7. AI TIMETABLE INGESTION & PARSING PIPELINE
# ============================================================================

class UploadedDocument(db.Model):
    """
    Raw timetable screenshot or PDF files uploaded for AI OCR/VLM ingestion.
    """
    __tablename__ = 'uploaded_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    filename = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500))
    file_type = db.Column(db.String(50)) # image/png, image/jpeg, application/pdf
    file_size_bytes = db.Column(db.Integer)
    storage_path = db.Column(db.String(500))
    upload_status = db.Column(db.String(30), default='uploaded') # uploaded, processing, parsed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parsing_jobs = db.relationship('ParsingJob', backref='document', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "upload_status": self.upload_status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ParsingJob(db.Model):
    """
    OCR/Vision extraction jobs for converting timetable documents into structured Ghost events.
    """
    __tablename__ = 'parsing_jobs'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('uploaded_documents.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    status = db.Column(db.String(30), default='pending') # pending, processing, completed, failed
    model_name = db.Column(db.String(100), default='gemini-vision')
    raw_response = db.Column(db.JSON, default=dict)
    extracted_event_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)

    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "status": self.status,
            "model_name": self.model_name,
            "extracted_event_count": self.extracted_event_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


# ============================================================================
# 8. NOTIFICATIONS & AUDIT LOGGING
# ============================================================================

class Notification(db.Model):
    """
    Tiered notification alerts: CRITICAL, HIGH, NORMAL, LOW, SILENT.
    """
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    priority = db.Column(db.String(20), default='NORMAL') # CRITICAL, HIGH, NORMAL, LOW, SILENT
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    action_type = db.Column(db.String(50)) # rebalance, capacity_warning, assumed_complete, recovery_prompt
    action_payload = db.Column(db.JSON, default=dict)

    is_read = db.Column(db.Boolean, default=False, index=True)
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "priority": self.priority,
            "title": self.title,
            "body": self.body,
            "action_type": self.action_type,
            "action_payload": self.action_payload or {},
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class NotificationPreference(db.Model):
    """
    User settings for alert filtering and lecture/recovery suppression.
    """
    __tablename__ = 'notification_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)

    enable_critical = db.Column(db.Boolean, default=True)
    enable_high = db.Column(db.Boolean, default=True)
    enable_normal = db.Column(db.Boolean, default=True)
    enable_low = db.Column(db.Boolean, default=False)

    quiet_hours_start = db.Column(db.Time, default=time(23, 0))
    quiet_hours_end = db.Column(db.Time, default=time(8, 0))
    mute_during_lectures = db.Column(db.Boolean, default=True)
    mute_during_recovery = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "enable_critical": self.enable_critical,
            "enable_high": self.enable_high,
            "enable_normal": self.enable_normal,
            "enable_low": self.enable_low,
            "quiet_hours_start": self.quiet_hours_start.strftime("%H:%M") if self.quiet_hours_start else None,
            "quiet_hours_end": self.quiet_hours_end.strftime("%H:%M") if self.quiet_hours_end else None,
            "mute_during_lectures": self.mute_during_lectures,
            "mute_during_recovery": self.mute_during_recovery
        }


class AuditLog(db.Model):
    """
    Audit trail for schedule adjustments, ghost confirmations, and critical actions.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    action = db.Column(db.String(100), nullable=False) # e.g. 'confirm_ghost_change', 'rebalance_applied'
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# 9. BACKWARDS COMPATIBILITY LAYER
# ============================================================================

class Task(db.Model):
    """
    Legacy Task model preserved for existing prototype blueprints (e.g. app/tasks.py).
    New code should use Activity directly.
    """
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Academic')
    deadline = db.Column(db.Date)
    importance = db.Column(db.Integer, default=2)
    effort_hours = db.Column(db.Float, default=1.0)
    effort_mental = db.Column(db.Integer, default=2)
    status = db.Column(db.String(20), default='todo')
    completed_at = db.Column(db.DateTime)
    parent_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'))
    is_moveable = db.Column(db.Boolean, default=True)

    # Legacy relationship to user
    user = db.relationship('User', back_populates='tasks')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "importance": self.importance,
            "effort_hours": self.effort_hours,
            "status": self.status,
            "is_moveable": self.is_moveable
        }


class CheckIn(db.Model):
    """
    Legacy CheckIn model preserved for existing app/wellbeing.py.
    """
    __tablename__ = 'checkins'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    date = db.Column(db.Date, default=date.today)
    mood = db.Column(db.Integer)
    stress = db.Column(db.Integer)
    note = db.Column(db.Text)

    user = db.relationship('User', backref=db.backref('checkins', lazy='dynamic'))


class TimerSession(db.Model):
    """
    Legacy TimerSession model preserved for existing timer routes.
    """
    __tablename__ = 'timer_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    mode = db.Column(db.String(20))
    duration_minutes = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('timer_sessions', lazy='dynamic'))
