from django.core.exceptions import ValidationError
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Audit records are append-only.')

    def delete(self):
        raise ValidationError('Audit records are append-only.')

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError('Audit records are append-only.')


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Created'
        UPDATE = 'update', 'Updated'
        DELETE = 'delete', 'Deleted'
        MEMBERSHIP = 'membership', 'Membership changed'

    # Snapshots deliberately have no FK: deleting an account cannot rewrite history.
    actor_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    actor_label = models.CharField(max_length=160)
    actor_role = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=12, choices=Action.choices)
    target_model = models.CharField(max_length=100, db_index=True)
    target_id = models.CharField(max_length=80, db_index=True)
    diff = models.JSONField(default=dict)
    source = models.CharField(max_length=12, choices=[('api', 'API'), ('admin', 'Django admin'), ('system', 'System')])
    entry_point = models.CharField(max_length=240, blank=True)
    request_id = models.UUIDField(null=True, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ['-timestamp', '-id']
        indexes = [models.Index(fields=['target_model', 'target_id', '-timestamp']), models.Index(fields=['action', '-timestamp'])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Audit records are append-only.')
        kwargs['force_insert'] = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Audit records are append-only.')
