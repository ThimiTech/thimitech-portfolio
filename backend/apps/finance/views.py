from datetime import date

from django.db import transaction
from django.db.models import Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.notifications.services import push
from apps.permissions.permissions import IsEmployee, IsFinance, IsSuperAdmin
from config.pagination import ServerListMixin
from . import exports, reports
from .fiscal import current_fy, fy_of, fy_range, parse_fy, recent_fys
from .models import (Account, Category, Expense, FiscalYearClose, Invoice, Payslip, SalaryStructure, Statement,
                     Transaction)
from .services import assert_open, import_rows, match_payments, new_payslip, parse_statement, summary_payload
from .serializers import (AccountSerializer, BulkSerializer, CategorySerializer, DecisionSerializer, ExpenseSerializer,
                          FinanceSummarySerializer, FiscalYearCloseSerializer, GenerateSerializer, ImportSerializer,
                          InvoiceSerializer, MyExpenseSerializer, MyPayslipSerializer, PaymentSerializer,
                          PayslipSerializer, PeriodSerializer, SalarySerializer, StatementSerializer,
                          TransactionSerializer)


def forbid_self(request, employee_id):
    """Separation of duties (as in attendance/leave): HR never sets or approves their own pay or expenses."""
    if employee_id == request.user.pk and not request.user.has_role('super_admin'):
        raise PermissionDenied('You cannot manage your own salary, payslips or expense decisions; ask another HR admin.')


def fy_param(request):
    fy = request.query_params.get('fy') or current_fy()
    try:
        parse_fy(fy)
    except ValueError as e:
        raise ValidationError({'fy': str(e)})
    return fy


def link_payment(instance, txn):
    """Attach the bank line that paid a payslip / claim / invoice to it."""
    if not txn:
        return
    field = {Payslip: 'payslip', Expense: 'expense', Invoice: 'invoice'}[type(instance)]
    setattr(txn, field, instance)
    if field != 'invoice' and not txn.employee_id:
        txn.employee = instance.employee
    if field == 'invoice' and instance.project_id and not txn.project_id:
        txn.project = instance.project
    txn.save()


class DraftViewSet(ServerListMixin, viewsets.ModelViewSet):
    permission_classes = [IsFinance]
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
            qs = qs.select_for_update(of=('self',))
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
        txn = extra.pop('transaction', None)
        instance.status = target
        for key, value in extra.items():
            setattr(instance, key, value)
        instance.save(update_fields=['status', *extra.keys()])
        link_payment(instance, txn)
        self.on_transition(instance, target)
        return Response(self.get_serializer(instance).data)

    def on_transition(self, instance, target):
        pass


@extend_schema(tags=['Finance'])
class SalaryViewSet(ServerListMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsFinance]
    queryset = SalaryStructure.objects.select_related('employee')
    serializer_class = SalarySerializer
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['employee__first_name', 'effective_from', 'basic']

    def get_queryset(self):
        qs = super().get_queryset()
        employee = self.request.query_params.get('employee')
        return qs.filter(employee_id=employee) if employee and employee.isdigit() else qs

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
    queryset = Payslip.objects.select_related('employee__profile', 'employee__salary_structure').prefetch_related('transactions')
    serializer_class = PayslipSerializer
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['period', 'status', 'employee__first_name']
    status_choices = [c for c, _ in Payslip._meta.get_field('status').choices]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs, p = super().get_queryset(), self.request.query_params
        if p.get('period'):
            qs = qs.filter(period=p['period'])
        if p.get('employee', '').isdigit():
            qs = qs.filter(employee_id=p['employee'])
        if p.get('fy'):
            qs = qs.filter(period__range=fy_range(fy_param(self.request)))
        return qs

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
        d = serializer.validated_data
        salary = SalaryStructure.objects.select_for_update().get(pk=d['salary'].pk)
        forbid_self(request, salary.employee_id)
        if not salary.active:
            raise ValidationError('This salary structure is inactive.')
        if Payslip.objects.filter(employee=salary.employee, period=d['period']).exists():
            raise ValidationError('A payslip already exists for this employee and month, including void records.')
        slip = new_payslip(salary, d['period'], request.user, d.get('working_days'), d.get('days_worked'), d.get('bonus'))
        return Response(self.get_serializer(slip).data, status=201)

    @extend_schema(request=PeriodSerializer)
    @action(detail=False, methods=['post'], url_path='generate-month')
    @transaction.atomic
    def generate_month(self, request):
        """Draft payslips for every active salary structure effective in the month that has none yet."""
        s = PeriodSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        period, wd = s.validated_data['period'], s.validated_data.get('working_days')
        created, skipped = [], []
        for salary in SalaryStructure.objects.select_for_update().filter(
                active=True, employee__is_active=True, effective_from__lte=reports.month_end(period)).exclude(
                employee__role='guest').select_related('employee'):
            name = salary.employee.get_full_name() or salary.employee.email
            if salary.employee_id == request.user.pk and not request.user.has_role('super_admin'):
                skipped.append(f'{name} (your own pay; another admin generates it)')
            elif Payslip.objects.filter(employee=salary.employee, period=period).exists():
                skipped.append(f'{name} (already has one)')
            else:
                created.append(new_payslip(salary, period, request.user, wd, wd).pk)
        return Response({'created': len(created), 'skipped': skipped}, status=201 if created else 200)

    @extend_schema(request=PeriodSerializer)
    @action(detail=False, methods=['post'], url_path='issue-month')
    @transaction.atomic
    def issue_month(self, request):
        s = PeriodSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        drafts = Payslip.objects.select_for_update().filter(period=s.validated_data['period'], status='draft')
        if not request.user.has_role('super_admin'):
            drafts = drafts.exclude(employee=request.user)
        issued = 0
        for slip in drafts.select_related('employee'):
            slip.status, slip.issued_at = 'issued', timezone.now()
            slip.save(update_fields=['status', 'issued_at'])
            self.on_transition(slip, 'issued')
            issued += 1
        return Response({'issued': issued})

    @extend_schema(request=PeriodSerializer)
    @action(detail=False, methods=['post'], url_path='match-payments')
    def match_payments(self, request):
        """Find the bank line that paid each slip of the month; link it and mark the slip paid."""
        s = PeriodSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(match_payments(s.validated_data['period'], request.user))


@extend_schema(tags=['Finance'])
class InvoiceViewSet(PaymentActions, DraftViewSet):
    queryset = Invoice.objects.select_related('project').prefetch_related('items')
    serializer_class = InvoiceSerializer
    search_fields = ['number', 'client_name', 'client_email']
    ordering_fields = ['issue_date', 'due_date', 'number', 'client_name', 'status']
    status_choices = [c for c, _ in Invoice._meta.get_field('status').choices]

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get('project', '')
        return qs.filter(project_id=project) if project.isdigit() else qs


class ClaimActions:
    """Submit (own claim) -- shared by the finance register and My claims."""
    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit(self, request, pk=None):
        return self.transition(['draft', 'rejected'], 'submitted', decision_note='', decided_by=None, decided_at=None)


@extend_schema(tags=['Finance'])
class ExpenseViewSet(ClaimActions, DraftViewSet):
    queryset = Expense.objects.select_related('employee', 'category', 'project').prefetch_related('files')
    serializer_class = ExpenseSerializer
    search_fields = ['description', 'category__name', 'employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['date', 'amount', 'status', 'employee__first_name']
    status_choices = [c for c, _ in Expense._meta.get_field('status').choices]
    editable_statuses = ['draft', 'rejected']
    self_service_actions = ('update', 'partial_update', 'destroy', 'submit')  # but never approve/reject/pay

    def get_queryset(self):
        qs, p = super().get_queryset(), self.request.query_params
        for f in ('employee', 'project', 'category'):
            if p.get(f, '').isdigit():
                qs = qs.filter(**{f'{f}_id': p[f]})
        if p.get('fy'):
            qs = qs.filter(date__range=fy_range(fy_param(self.request)))
        return qs

    def on_transition(self, claim, target):
        if target in ('approved', 'rejected', 'paid'):
            push([claim.employee], 'claim_decided', f'Your claim "{claim.description[:60]}" was {target}',
                 claim.decision_note or f'{claim.currency} {claim.amount}', '/app/my-pay')

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
class MyExpenseViewSet(ClaimActions, DraftViewSet):
    """My claims: money I spent for the company. Create, edit drafts, attach receipts (drive upload with expense=id), submit."""
    permission_classes = [IsEmployee]
    serializer_class = MyExpenseSerializer
    queryset = Expense.objects.select_related('employee', 'category', 'project').prefetch_related('files')
    status_choices = [c for c, _ in Expense._meta.get_field('status').choices]
    editable_statuses = ['draft', 'rejected']
    self_service_actions = ('update', 'partial_update', 'destroy', 'submit')
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'status']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Expense.objects.none()
        return super().get_queryset().filter(employee=self.request.user)

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user, created_by=self.request.user)


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
    permission_classes = [IsFinance]

    @extend_schema(responses=FinanceSummarySerializer)
    def get(self, request):
        return Response(summary_payload())


# ---------------------------------------------------------------- books

class ProtectedDeleteMixin:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('This is in use by recorded entries. Deactivate it instead.')


@extend_schema(tags=['Finance'])
class CategoryViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """Everyone with a staff account can read categories (claims need them); finance roles manage them."""
    serializer_class = CategorySerializer
    pagination_class = None

    def get_permissions(self):
        return [IsEmployee()] if self.request.method in ('GET', 'HEAD', 'OPTIONS') else [IsFinance()]

    def get_queryset(self):
        qs = Category.objects.annotate(entries=Count('transactions'))
        kind = self.request.query_params.get('kind')
        return qs.filter(kind__in=kind.split(',')) if kind else qs


@extend_schema(tags=['Finance'])
class AccountViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsFinance]
    serializer_class = AccountSerializer
    queryset = Account.objects.annotate(entries=Count('transactions'))
    pagination_class = None


def running_balance():
    """Balance after each line within its account (opening + every earlier line), independent of list filters."""
    before = Transaction.objects.filter(account=OuterRef('account')).filter(
        Q(date__lt=OuterRef('date')) | Q(date=OuterRef('date'), id__lte=OuterRef('id'))).order_by().values('account').annotate(
        s=Sum(F('credit') - F('debit'))).values('s')
    return F('account__opening_balance') + Coalesce(Subquery(before), Value(0), output_field=DecimalField(max_digits=16, decimal_places=2))


@extend_schema(tags=['Finance'])
class TransactionViewSet(ServerListMixin, viewsets.ModelViewSet):
    """The ledger. Filters: account, category (id or "none"), kind, status, fy, date_from, date_to, employee, project,
    payslip, expense, invoice, direction=in|out, party. List lines carry `balance` (running, per account)."""
    permission_classes = [IsFinance]
    serializer_class = TransactionSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ['description', 'party', 'reference', 'note', 'category__name']
    ordering_fields = ['date', 'debit', 'credit', 'party', 'status']
    status_choices = Transaction.Status.values

    def get_queryset(self):
        qs = Transaction.objects.select_related('account', 'category', 'employee', 'project', 'payslip__employee',
                                                'invoice', 'expense').annotate(files_count=Count('files'), balance=running_balance())
        p = self.request.query_params
        for f in ('account', 'employee', 'project', 'payslip', 'expense', 'invoice'):
            if p.get(f, '').isdigit():
                qs = qs.filter(**{f'{f}_id': p[f]})
        if p.get('category') == 'none':
            qs = qs.filter(category__isnull=True)
        elif p.get('category', '').isdigit():
            qs = qs.filter(category_id=p['category'])
        if p.get('kind'):
            qs = qs.filter(category__kind=p['kind'])
        if p.get('fy'):
            qs = qs.filter(date__range=fy_range(fy_param(self.request)))
        if p.get('date_from'):
            qs = qs.filter(date__gte=p['date_from'])
        if p.get('date_to'):
            qs = qs.filter(date__lte=p['date_to'])
        if p.get('direction') in ('in', 'out'):
            qs = qs.filter(**{'credit__gt' if p['direction'] == 'in' else 'debit__gt': 0})
        if p.get('party'):
            qs = qs.filter(party__iexact=p['party'])
        if p.get('status') and self.action == 'totals':
            qs = qs.filter(status=p['status'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, txn):
        assert_open(txn.date)
        txn.delete()

    @action(detail=False, methods=['get'])
    def totals(self, request):
        qs = self.filter_queryset(self.get_queryset()).order_by()
        t = qs.aggregate(dr=Sum('debit'), cr=Sum('credit'), n=Count('id'))
        by = qs.values('category__name').annotate(dr=Sum('debit'), cr=Sum('credit'), n=Count('id')).order_by('-dr')
        return Response({'entries': t['n'], 'out': str(t['dr'] or 0), 'in': str(t['cr'] or 0),
                         'by_category': [{'name': r['category__name'] or 'Uncategorized', 'out': str(r['dr']), 'in': str(r['cr']),
                                          'entries': r['n']} for r in by]})

    @action(detail=False, methods=['get'])
    def parties(self, request):
        """Distinct party names, most used first (autocomplete)."""
        rows = Transaction.objects.exclude(party='').values('party').annotate(n=Count('id')).order_by('-n')[:300]
        return Response([r['party'] for r in rows])

    @extend_schema(request=BulkSerializer)
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def bulk(self, request):
        """Set category / status / employee / project on many lines at once (the review queue)."""
        s = BulkSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        changes = {k: d[k] for k in ('category', 'status', 'employee', 'project') if k in d}
        if not changes:
            raise ValidationError('Nothing to change.')
        updated = 0
        for txn in Transaction.objects.select_for_update().filter(pk__in=d['ids']):
            assert_open(txn.date)
            for k, v in changes.items():
                setattr(txn, k, v)
            txn.save()  # per row, so the audit log records each change
            updated += 1
        return Response({'updated': updated})

    @extend_schema(request=ImportSerializer)
    @action(detail=False, methods=['post'], url_path='import')
    def import_statement(self, request):
        """Upload a bank statement (CSV/XLSX). dry_run=true (default) returns a preview; false adds the new lines."""
        s = ImportSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        rows = parse_statement(d['file'])
        if len(rows) > 5000:
            raise ValidationError({'file': 'Split statements larger than 5,000 lines.'})
        return Response(import_rows(d['account'], rows, request.user, dry_run=d['dry_run']))


@extend_schema(tags=['Finance'])
class StatementViewSet(viewsets.ModelViewSet):
    """Statement periods per account, each with its reconciliation against the ledger."""
    permission_classes = [IsFinance]
    serializer_class = StatementSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Statement.objects.select_related('account').prefetch_related('files')
        account = self.request.query_params.get('account', '')
        return qs.filter(account_id=account) if account.isdigit() else qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, st):
        assert_open(st.end)
        st.delete()


@extend_schema(tags=['Finance'])
class FiscalYearViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """GET: every fiscal year with activity (newest first), closed or open. POST {name}: close a year. DELETE: reopen (super admin)."""
    serializer_class = FiscalYearCloseSerializer
    queryset = FiscalYearClose.objects.select_related('closed_by')
    pagination_class = None

    def get_permissions(self):
        return [IsSuperAdmin()] if self.action == 'destroy' else [IsFinance()]

    def list(self, request):
        first = Transaction.objects.order_by('date').values_list('date', flat=True).first()
        closed = {c.name: c for c in self.get_queryset()}
        return Response({'current': current_fy(), 'years': [
            {'name': fy, 'start': fy_range(fy)[0], 'end': fy_range(fy)[1], 'closed': fy in closed,
             'close': self.get_serializer(closed[fy]).data if fy in closed else None}
            for fy in recent_fys(first)]})

    def perform_create(self, serializer):
        if fy_range(serializer.validated_data['name'])[1] >= timezone.localdate():
            raise ValidationError({'name': 'A fiscal year can be closed only after it ends.'})
        serializer.save(closed_by=self.request.user)


@extend_schema(tags=['Finance'])
class ReportView(APIView):
    """GET /api/finance/reports/{overview|statutory|parties}/?fy=2082/83"""
    permission_classes = [IsFinance]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, name):
        fn = {'overview': reports.overview, 'statutory': reports.statutory, 'parties': reports.parties}.get(name)
        if not fn:
            raise ValidationError('Unknown report.')
        return Response(fn(fy_param(request)))


@extend_schema(tags=['Finance'])
class ExportView(APIView):
    """GET /api/finance/export/?what=ledger|payroll|statutory|claims|invoices|categories|parties|accounts|book&type=csv|xlsx&fy=&period=
    GET /api/finance/export/audit-pack/?fy= -> zip for the CA (workbook + README + that year's documents)."""
    permission_classes = [IsFinance]

    @extend_schema(responses={(200, 'application/octet-stream'): OpenApiTypes.BINARY})
    def get(self, request, pack=False):
        fy = fy_param(request)
        if pack:
            return exports.audit_pack(fy)
        what, fmt = request.query_params.get('what', 'book'), request.query_params.get('type', 'xlsx')
        if what != 'book' and what not in exports.SHEETS or fmt not in ('csv', 'xlsx'):
            raise ValidationError('Unknown export.')
        period = request.query_params.get('period')
        try:
            period = date.fromisoformat(period) if period else None
        except ValueError:
            raise ValidationError({'period': 'Use YYYY-MM-01.'})
        return exports.export(what, fmt, fy_of(period) if period else fy, period)


@extend_schema(tags=['Finance'])
class ProjectOptionsView(APIView):
    """Every project (id, name) for linking finance records; finance roles are often not project members."""
    permission_classes = [IsFinance]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        from apps.pm.models import Project
        return Response(list(Project.objects.order_by('name').values('id', 'name')))
