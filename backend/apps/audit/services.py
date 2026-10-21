import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models.fields.files import FieldFile
from .context import event_context
from .models import AuditLog
from .policy import PUBLIC_FIELDS, tracked_fields


def normalize(value):
    if isinstance(value, FieldFile):
        value = value.name
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def snapshot(instance):
    return {field.name: normalize(field.value_from_object(instance)) for field in tracked_fields(type(instance))}


def bounded(value):
    if isinstance(value, str):
        return value[:400] + ('…' if len(value) > 400 else '')
    if isinstance(value, list):
        return [bounded(item) for item in value[:50]] + (['[truncated]'] if len(value) > 50 else [])
    if isinstance(value, dict):
        return {str(key)[:80]: bounded(item) for key, item in list(value.items())[:30]}
    return value


def record_change(instance, action, before=None, after=None, *, using='default', membership=None):
    before, after = before or {}, after or {}
    fields = {f.name: f for f in tracked_fields(type(instance))}
    diff = {}
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old == new:
            continue
        public = key == membership or key in PUBLIC_FIELDS or (key in fields and fields[key].is_relation)
        diff[key] = {'before': bounded(old), 'after': bounded(new)} if public else {'redacted': True, 'changed': True}
    if not diff and action == 'update':
        return None
    return AuditLog.objects.using(using).create(
        target_model=instance._meta.label_lower, target_id=str(instance.pk), action=action,
        diff=diff, **event_context(),
    )


def record_created(instance, *, using='default'):
    return record_change(instance, 'create', after=snapshot(instance), using=using)


@transaction.atomic
def audited_update(queryset, **changes):
    """For existing bounded bulk business updates: lock rows and retain per-row diffs."""
    count = 0
    for instance in queryset.select_for_update():
        for key, value in changes.items():
            setattr(instance, key, value)
        instance.save(update_fields=list(changes))
        count += 1
    return count
