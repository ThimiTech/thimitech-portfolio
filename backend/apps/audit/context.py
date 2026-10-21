from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

current_context = ContextVar('audit_context', default=None)


@contextmanager
def system_context(entry_point):
    token = current_context.set({'request': None, 'source': 'system', 'entry_point': entry_point, 'request_id': uuid4()})
    try:
        yield
    finally:
        current_context.reset(token)


def event_context():
    context = current_context.get() or {}
    request = context.get('request')
    actor = getattr(request, 'user', None)
    authenticated = actor is not None and actor.is_authenticated
    route = getattr(getattr(request, 'resolver_match', None), 'route', '')
    return {
        'actor_id': actor.pk if authenticated else None,
        'actor_label': ((actor.get_full_name() or f'User #{actor.pk}')[:160] if authenticated else ('Anonymous' if request else 'System')),
        'actor_role': actor.role if authenticated else '',
        'source': context.get('source', 'system'),
        'entry_point': (f'{request.method} {route}' if request else context.get('entry_point', 'orm'))[:240],
        'request_id': context.get('request_id'),
    }
