from .policy import tracked_fields
from django.db import connections
from .services import normalize, record_change, snapshot


def before_save(sender, instance, raw=False, using='default', **kwargs):
    if raw:
        return
    fields = tracked_fields(sender)
    queryset = sender._default_manager.using(using).filter(pk=instance.pk)
    if connections[using].in_atomic_block:
        queryset = queryset.select_for_update()
    old = queryset.values(*[f.attname for f in fields]).first() if instance.pk else None
    instance._audit_before = {f.name: normalize(old[f.attname]) for f in fields} if old else {}


def after_save(sender, instance, created, raw=False, using='default', **kwargs):
    if raw:
        return
    # Reload saved fields so save(update_fields=...) never audits unsaved in-memory edits.
    saved = sender._default_manager.using(using).get(pk=instance.pk)
    record_change(saved, 'create' if created else 'update', getattr(instance, '_audit_before', {}), snapshot(saved), using=using)


def before_delete(sender, instance, using='default', **kwargs):
    saved = sender._default_manager.using(using).select_for_update().get(pk=instance.pk)
    instance._audit_deleted = snapshot(saved)


def after_delete(sender, instance, using='default', **kwargs):
    record_change(instance, 'delete', before=instance._audit_deleted, using=using)


def membership_receiver(owner, field):
    def changed(sender, instance, action, reverse, pk_set, using='default', **kwargs):
        key = f'_audit_m2m_{sender._meta.label_lower}_{reverse}'
        if action.startswith('pre_'):
            if reverse:
                ids = pk_set if pk_set is not None else owner._default_manager.using(using).filter(**{field.name: instance.pk}).values_list('pk', flat=True)
                targets = owner._default_manager.using(using).filter(pk__in=ids)
            else:
                targets = [instance]
            setattr(instance, key, [(obj, list(getattr(obj, field.name).using(using).order_by('pk').values_list('pk', flat=True))) for obj in targets])
        elif action.startswith('post_'):
            for obj, before in getattr(instance, key, []):
                after = list(getattr(obj, field.name).using(using).order_by('pk').values_list('pk', flat=True))
                if before != after:
                    record_change(obj, 'membership', {field.name: before}, {field.name: after}, membership=field.name, using=using)
            if hasattr(instance, key):
                delattr(instance, key)
    return changed
