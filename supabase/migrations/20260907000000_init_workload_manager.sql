CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	is_active_account BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS profiles (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	target_daily_capacity FLOAT, 
	target_weekly_capacity FLOAT, 
	preferred_study_start TIME WITHOUT TIME ZONE, 
	preferred_study_end TIME WITHOUT TIME ZONE, 
	typical_commute_minutes INTEGER, 
	task_extension_rate FLOAT, 
	intervention_style VARCHAR(20), 
	assumed_complete_enabled BOOLEAN, 
	suppress_notifications_during_recovery BOOLEAN, 
	dimension_weights JSON, 
	personal_modifiers JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedules (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	semester VARCHAR(50), 
	academic_year VARCHAR(50), 
	is_active BOOLEAN, 
	valid_from DATE, 
	valid_until DATE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedule_recurrences (
	id SERIAL NOT NULL, 
	schedule_id INTEGER NOT NULL, 
	course_code VARCHAR(50), 
	course_name VARCHAR(150) NOT NULL, 
	event_type VARCHAR(50), 
	day_of_week INTEGER NOT NULL, 
	start_time TIME WITHOUT TIME ZONE NOT NULL, 
	end_time TIME WITHOUT TIME ZONE NOT NULL, 
	location VARCHAR(150), 
	is_fixed BOOLEAN, 
	confidence_score FLOAT, 
	raw_metadata JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(schedule_id) REFERENCES schedules (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS locations (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	category VARCHAR(50), 
	address VARCHAR(255), 
	latitude FLOAT, 
	longitude FLOAT, 
	opening_time TIME WITHOUT TIME ZONE, 
	closing_time TIME WITHOUT TIME ZONE, 
	typical_travel_minutes INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS errand_clusters (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	scheduled_date DATE NOT NULL, 
	start_time TIME WITHOUT TIME ZONE, 
	end_time TIME WITHOUT TIME ZONE, 
	total_duration_minutes INTEGER, 
	saved_travel_minutes INTEGER, 
	status VARCHAR(30), 
	route_order JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS uploaded_documents (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	file_url VARCHAR(500), 
	file_type VARCHAR(50), 
	file_size_bytes INTEGER, 
	storage_path VARCHAR(500), 
	upload_status VARCHAR(30), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS parsing_jobs (
	id SERIAL NOT NULL, 
	document_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	status VARCHAR(30), 
	model_name VARCHAR(100), 
	raw_response JSON, 
	extracted_event_count INTEGER, 
	error_message TEXT, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES uploaded_documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recovery_windows (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	duration_minutes INTEGER NOT NULL, 
	recovery_type VARCHAR(50), 
	is_protected BOOLEAN, 
	is_utilized BOOLEAN, 
	suppress_notifications BOOLEAN, 
	recommended_actions JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS commitments (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	category VARCHAR(50), 
	estimated_hours FLOAT NOT NULL, 
	proposed_start TIMESTAMP WITHOUT TIME ZONE, 
	proposed_end TIMESTAMP WITHOUT TIME ZONE, 
	intensity VARCHAR(20), 
	priority VARCHAR(20), 
	simulated_weekly_load_before FLOAT, 
	simulated_weekly_load_after FLOAT, 
	simulation_verdict VARCHAR(30), 
	displaced_summary JSON, 
	status VARCHAR(30), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ghost_changes (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	source_type VARCHAR(50) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	reason TEXT, 
	confidence_score FLOAT, 
	status VARCHAR(30), 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	priority VARCHAR(20), 
	title VARCHAR(150) NOT NULL, 
	body TEXT NOT NULL, 
	action_type VARCHAR(50), 
	action_payload JSON, 
	is_read BOOLEAN, 
	is_sent BOOLEAN, 
	sent_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notification_preferences (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	enable_critical BOOLEAN, 
	enable_high BOOLEAN, 
	enable_normal BOOLEAN, 
	enable_low BOOLEAN, 
	quiet_hours_start TIME WITHOUT TIME ZONE, 
	quiet_hours_end TIME WITHOUT TIME ZONE, 
	mute_during_lectures BOOLEAN, 
	mute_during_recovery BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(50), 
	entity_id INTEGER, 
	details JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	schedule_event_id INTEGER, 
	parent_id INTEGER, 
	title VARCHAR(150) NOT NULL, 
	description TEXT, 
	category VARCHAR(50) NOT NULL, 
	activity_type VARCHAR(80), 
	stat_vector JSON NOT NULL, 
	start_time TIMESTAMP WITHOUT TIME ZONE, 
	end_time TIMESTAMP WITHOUT TIME ZONE, 
	duration_minutes INTEGER NOT NULL, 
	continuous_minutes INTEGER, 
	intensity VARCHAR(20), 
	priority VARCHAR(20), 
	is_fixed BOOLEAN, 
	deadline TIMESTAMP WITHOUT TIME ZONE, 
	location_id INTEGER, 
	location_name VARCHAR(150), 
	travel_time_minutes INTEGER, 
	is_recurring BOOLEAN, 
	is_clusterable BOOLEAN, 
	recovery_type VARCHAR(50), 
	status VARCHAR(30), 
	confidence FLOAT, 
	assumed_complete_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(schedule_event_id) REFERENCES schedule_events (id) ON DELETE SET NULL, 
	FOREIGN KEY(parent_id) REFERENCES activities (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS schedule_events (
	id SERIAL NOT NULL, 
	schedule_id INTEGER NOT NULL, 
	recurrence_id INTEGER, 
	user_id INTEGER, 
	title VARCHAR(150) NOT NULL, 
	event_type VARCHAR(50), 
	day_of_week INTEGER, 
	date DATE, 
	start_time TIME WITHOUT TIME ZONE NOT NULL, 
	end_time TIME WITHOUT TIME ZONE NOT NULL, 
	location VARCHAR(150), 
	is_fixed BOOLEAN, 
	status VARCHAR(30), 
	activity_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(schedule_id) REFERENCES schedules (id) ON DELETE CASCADE, 
	FOREIGN KEY(recurrence_id) REFERENCES schedule_recurrences (id) ON DELETE SET NULL, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(activity_id) REFERENCES activities (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS errand_details (
	id SERIAL NOT NULL, 
	activity_id INTEGER NOT NULL, 
	location_id INTEGER, 
	cluster_id INTEGER, 
	errand_subtype VARCHAR(50), 
	estimated_errand_minutes INTEGER, 
	travel_time_minutes INTEGER, 
	physical_intensity VARCHAR(20), 
	preferred_window VARCHAR(50), 
	is_clustered BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (activity_id), 
	FOREIGN KEY(activity_id) REFERENCES activities (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL, 
	FOREIGN KEY(cluster_id) REFERENCES errand_clusters (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ghost_change_items (
	id SERIAL NOT NULL, 
	ghost_change_id INTEGER NOT NULL, 
	source_event_id INTEGER, 
	source_activity_id INTEGER, 
	operation VARCHAR(20) NOT NULL, 
	old_start TIMESTAMP WITHOUT TIME ZONE, 
	old_end TIMESTAMP WITHOUT TIME ZONE, 
	new_start TIMESTAMP WITHOUT TIME ZONE, 
	new_end TIMESTAMP WITHOUT TIME ZONE, 
	payload JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ghost_change_id) REFERENCES ghost_changes (id) ON DELETE CASCADE, 
	FOREIGN KEY(source_event_id) REFERENCES schedule_events (id) ON DELETE SET NULL, 
	FOREIGN KEY(source_activity_id) REFERENCES activities (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workload_events (
	id SERIAL NOT NULL, 
	activity_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	academic_raw FLOAT, 
	academic_display FLOAT, 
	work_raw FLOAT, 
	work_display FLOAT, 
	social_raw FLOAT, 
	social_display FLOAT, 
	health_raw FLOAT, 
	health_display FLOAT, 
	errands_raw FLOAT, 
	errands_display FLOAT, 
	duration_multiplier FLOAT, 
	intensity_multiplier FLOAT, 
	continuity_modifier FLOAT, 
	timing_modifier FLOAT, 
	context_modifier FLOAT, 
	is_recovery BOOLEAN, 
	applied_cap FLOAT, 
	calculated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(activity_id) REFERENCES activities (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workload_snapshots (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	snapshot_type VARCHAR(20), 
	academic_load FLOAT, 
	work_load FLOAT, 
	social_load FLOAT, 
	health_load FLOAT, 
	errands_load FLOAT, 
	overall_score FLOAT, 
	peak_penalty FLOAT, 
	compression_penalty FLOAT, 
	recovery_deficit_penalty FLOAT, 
	burn_rate FLOAT, 
	status_level VARCHAR(20), 
	limiting_factor VARCHAR(50), 
	raw_details JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	title VARCHAR(140) NOT NULL, 
	description TEXT, 
	category VARCHAR(50), 
	deadline DATE, 
	importance INTEGER, 
	effort_hours FLOAT, 
	effort_mental INTEGER, 
	status VARCHAR(20), 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	parent_id INTEGER, 
	is_moveable BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(parent_id) REFERENCES tasks (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS checkins (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	date DATE, 
	mood INTEGER, 
	stress INTEGER, 
	note TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS timer_sessions (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	mode VARCHAR(20), 
	duration_minutes INTEGER, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Sample Seed Data for immediate testing
INSERT INTO users (username, email, password_hash, is_active_account, created_at)
VALUES ('demo_student', 'demo@university.edu', 'pbkdf2:sha256:600000', true, NOW())
ON CONFLICT (username) DO NOTHING;

INSERT INTO profiles (user_id, target_daily_capacity, target_weekly_capacity, intervention_style)
SELECT id, 80.0, 85.0, 'balanced' FROM users WHERE username = 'demo_student'
ON CONFLICT (user_id) DO NOTHING;