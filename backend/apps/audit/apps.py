from django.apps import AppConfig, apps
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed


class AuditConfig(AppConfig):
    name = 'apps.audit'

    def ready(self):
        from .policy import tracked
        from .signals import before_save, after_save, before_delete, after_delete, membership_receiver
        for model in apps.get_models():
            if not tracked(model):
                continue
            label = model._meta.label_lower
            pre_save.connect(before_save, sender=model, dispatch_uid=f'audit.pre.{label}')
            post_save.connect(after_save, sender=model, dispatch_uid=f'audit.post.{label}')
            pre_delete.connect(before_delete, sender=model, dispatch_uid=f'audit.pre_delete.{label}')
            post_delete.connect(after_delete, sender=model, dispatch_uid=f'audit.delete.{label}')
            for field in model._meta.local_many_to_many:
                m2m_changed.connect(membership_receiver(model, field), sender=field.remote_field.through, weak=False, dispatch_uid=f'audit.m2m.{label}.{field.name}')
