TRACKED_APPS = {'users', 'org', 'attendance', 'leave', 'calendar_app', 'notices', 'pm', 'finance', 'inventory', 'projects', 'services', 'team', 'jobs'}
EXCLUDED_MODELS = {'notices.noticeread'}
EXCLUDED_FIELDS = {'id', 'created_at', 'updated_at', 'date_joined', 'last_login', 'emailed_at'}
# Everything else, including new fields, defaults to redacted. FK identities are metadata.
PUBLIC_FIELDS = {
    'name', 'title', 'key', 'code', 'role', 'is_active', 'active', 'is_staff', 'is_superuser',
    'status', 'date', 'start_date', 'end_date', 'start', 'end', 'due_date', 'due_back',
    'period', 'effective_from', 'position', 'priority', 'estimate', 'labels', 'archived',
    'completed', 'currency', 'category', 'tag', 'kind', 'quantity', 'days', 'half_day',
    'is_paid', 'annual_quota', 'is_optional', 'recurring', 'work_start', 'work_end',
    'late_grace_minutes', 'weekend_days', 'work_mode', 'source', 'check_in', 'check_out',
    'publish_at', 'expires_at', 'pinned', 'audience', 'employment_type', 'join_date',
    'assigned_at', 'returned_at', 'return_condition', 'issued_at', 'paid_at', 'decided_at',
}


def tracked(model):
    return model._meta.app_label in TRACKED_APPS and model._meta.label_lower not in EXCLUDED_MODELS and not model._meta.auto_created


def tracked_fields(model):
    return [f for f in model._meta.concrete_fields if not f.primary_key and f.name not in EXCLUDED_FIELDS]
