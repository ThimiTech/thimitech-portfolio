from uuid import uuid4
from django.db import transaction
from .context import current_context


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        source = 'admin' if request.path.startswith('/admin/') else 'api'
        request_id = uuid4()
        token = current_context.set({'request': request, 'source': source, 'request_id': request_id})
        try:
            mutation = request.method not in ('GET', 'HEAD', 'OPTIONS') and request.path.startswith(('/api/', '/admin/'))
            if mutation:
                with transaction.atomic():
                    response = self.get_response(request)
                    if response.status_code >= 400:
                        transaction.set_rollback(True)
            else:
                response = self.get_response(request)
            response['X-Request-ID'] = str(request_id)
            return response
        finally:
            current_context.reset(token)
