from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.notifications.services import push
from apps.permissions.permissions import IsEmployee, IsHRAdmin
from config.pagination import ServerListMixin
from .models import SalaryStructure, Payslip, Expense, Invoice
from .services import summary_payload
from .serializers import MyPayslipSerializer, SalarySerializer, PayslipSerializer, GenerateSerializer, ExpenseSerializer, InvoiceSerializer, PaymentSerializer, DecisionSerializer, FinanceSummarySerializer


def forbid_self(request, employee_id):
    """Separation of duties (as in attendance/leave): HR never sets or approves their own pay or expenses."""
    if employee_id == request.user.pk and not request.user.has_role('super_admin'):
        raise PermissionDenied('You cannot manage your own salary, payslips or expense decisions; ask another HR admin.')


class DraftViewSet(ServerListMixin, viewsets.ModelViewSet):
    permission_classes = [IsHRAdmin]
    editable_statuses = ['draft']
    self_service_actions = ()  # write actions allowed on your own record

    def get_object(self):
        obj = super().get_object()
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS') and self.action not in self.self_service_actions:
            forbid_self(self.request, getattr(obj, 'employee_id', None))
        return obj

    def get_queryset(self):
        qs = self.queryset.all()
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            qs = qs.select_for_update()
        return qs

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        if self.get_object().status not in self.editable_statuses:
            raise ValidationError('This record is finalized or awaiting a decision. Its amounts cannot be edited.')
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        if self.get_object().status != 'draft':
            raise ValidationError('Only drafts can be deleted. Keep finalized records for history.')
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def transition(self, allowed, target, **extra):
        instance = self.get_object()
        if instance.status not in allowed:
            raise ValidationError(f'Cannot change {instance.status} to {target}.')
        instance.status = target
        for key, value in extra.items():
            setattr(instance, key, value)
        instance.save(update_fields=['status', *extra.keys()])
        self.on_transition(instance, target)
        return Response(self.get_serializer(instance).data)

    def on_transition(self, instance, target):
        pass


@extend_schema(tags=['Finance'])
class SalaryViewSet(ServerListMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsHRAdmin]
    queryset = SalaryStructure.objects.select_related('employee')
    serializer_class = SalarySerializer
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['employee__first_name', 'effective_from', 'basic']

    def perform_create(self, serializer):
        forbid_self(self.request, serializer.validated_data['employee'].pk)
        serializer.save()

    def perform_update(self, serializer):
        forbid_self(self.request, serializer.instance.employee_id)
        serializer.save()


class PaymentActions:
    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def issue(self, request, pk=None):
        return self.transition(['draft'], 'issued', issued_at=timezone.now())

    @extend_schema(request=PaymentSerializer)
    @action(detail=True, methods=['post'], url_path='mark-paid')
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        data = PaymentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return self.transition(['issued'], 'paid', paid_at=timezone.now(), **data.validated_data)

    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def void(self, request, pk=None):
        return self.transition(['draft', 'issued'], 'void')


@extend_schema(tags=['Finance'])
class PayslipViewSet(PaymentActions, DraftViewSet):
    queryset = Payslip.objects.select_related('employee')
    serializer_class = PayslipSerializer
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['period', 'status', 'employee__first_name']
    status_choices = [c for c, _ in Payslip._meta.get_field('status').choices]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def create(self, request, *args, **kwargs):
        raise ValidationError('Use the generate endpoint to create a salary snapshot.')

    def on_transition(self, slip, target):
        if target == 'issued':
            push([slip.employee], 'payslip_issued', f'Your payslip for {slip.period:%B %Y} was issued',
                 f'Net pay: {slip.currency} {slip.net}.', f'/app/my-pay/{slip.pk}')

    @extend_schema(request=GenerateSerializer, responses=PayslipSerializer)
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def generate(self, request):
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        salary = SalaryStructure.objects.select_for_update().get(pk=serializer.validated_data['salary'].pk)
        forbid_self(request, salary.employee_id)
        if not salary.active:
            raise ValidationError('This salary structure is inactive.')
        slip, created = Payslip.objects.get_or_create(employee=salary.employee, period=serializer.validated_data['period'], defaults={'basic': salary.basic, 'allowances': salary.allowances, 'deductions': salary.deductions, 'created_by': request.user})
        if not created:
            raise ValidationError('A payslip already exists for this employee and month, including void records.')
        return Response(self.get_serializer(slip).data, status=201)


@extend_schema(tags=['Finance'])
class InvoiceViewSet(PaymentActions, DraftViewSet):
    queryset = Invoice.objects.prefetch_related('items')
    serializer_class = InvoiceSerializer
    search_fields = ['number', 'client_name', 'client_email']
    ordering_fields = ['issue_date', 'due_date', 'number', 'client_name', 'status']
    status_choices = [c for c, _ in Invoice._meta.get_field('status').choices]


@extend_schema(tags=['Finance'])
class ExpenseViewSet(DraftViewSet):
    queryset = Expense.objects.select_related('employee')
    serializer_class = ExpenseSerializer
    search_fields = ['description', 'category', 'employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['date', 'amount', 'status', 'employee__first_name']
    status_choices = [c for c, _ in Expense._meta.get_field('status').choices]
    editable_statuses = ['draft', 'rejected']
    self_service_actions = ('update', 'partial_update', 'destroy', 'submit')  # but never approve/reject/pay

    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit(self, request, pk=None):
        return self.transition(['draft', 'rejected'], 'submitted', decision_note='', decided_by=None, decided_at=None)

    def decide(self, request, status):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.transition(['submitted'], status, decided_by=request.user, decided_at=timezone.now(), **serializer.validated_data)

    @extend_schema(request=DecisionSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):
        return self.decide(request, 'approved')

    @extend_schema(request=DecisionSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reject(self, request, pk=None):
        return self.decide(request, 'rejected')

    @extend_schema(request=PaymentSerializer)
    @action(detail=True, methods=['post'], url_path='mark-paid')
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.transition(['approved'], 'paid', paid_at=timezone.now(), **serializer.validated_data)


@extend_schema(tags=['Finance'])
class MyPayslipViewSet(viewsets.ReadOnlyModelViewSet):
    """My pay: the caller's own issued/paid payslips. Drafts and void slips are never shown; no one else's, ever."""
    permission_classes = [IsEmployee]
    serializer_class = MyPayslipSerializer
    VISIBLE = ('issued', 'paid')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Payslip.objects.none()
        return Payslip.objects.filter(employee=self.request.user, status__in=self.VISIBLE).select_related(
            'employee__profile__department')


@extend_schema(tags=['Finance'])
class SummaryView(APIView):
    permission_classes = [IsHRAdmin]

    @extend_schema(responses=FinanceSummarySerializer)
    def get(self, request):
        return Response(summary_payload())
