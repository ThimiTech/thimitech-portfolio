from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination


class OptionalPagination(PageNumberPagination):
    """Pages only when the client sends ?page=, so existing callers that expect a bare list keep working.
    Paged response: {count, next, previous, results}."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if self.page_query_param not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)


class ServerListMixin:
    """?page=&page_size=&search=&ordering=&status= for a list endpoint. Set search_fields / ordering_fields
    (an allowlist; unknown ordering fields are ignored) and optionally status_choices."""
    pagination_class = OptionalPagination
    filter_backends = [SearchFilter, OrderingFilter]
    status_choices = ()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        status = self.request.query_params.get('status') if self.action == 'list' else None
        if status and self.status_choices:
            if status not in self.status_choices:
                raise ValidationError({'status': f'Must be one of: {", ".join(self.status_choices)}.'})
            queryset = queryset.filter(status=status)
        # pk tie-breaker: LIMIT/OFFSET over a non-unique sort can repeat or skip rows between pages
        return queryset.order_by(*(queryset.query.order_by or queryset.model._meta.ordering), 'pk')
