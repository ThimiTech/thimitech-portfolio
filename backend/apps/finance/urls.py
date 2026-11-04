from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (AccountViewSet, CategoryViewSet, ExpenseViewSet, ExportView, FiscalYearViewSet, InvoiceViewSet, ProjectOptionsView,
                    MyExpenseViewSet, MyPayslipViewSet, PayslipViewSet, ReportView, SalaryViewSet, StatementViewSet,
                    SummaryView, TransactionViewSet)
router = DefaultRouter()
router.register('my-payslips', MyPayslipViewSet, basename='finance-my-payslip')
router.register('my-expenses', MyExpenseViewSet, basename='finance-my-expense')
router.register('salaries', SalaryViewSet, basename='finance-salary')
router.register('payslips', PayslipViewSet, basename='finance-payslip')
router.register('expenses', ExpenseViewSet, basename='finance-expense')
router.register('invoices', InvoiceViewSet, basename='finance-invoice')
router.register('categories', CategoryViewSet, basename='finance-category')
router.register('accounts', AccountViewSet, basename='finance-account')
router.register('transactions', TransactionViewSet, basename='finance-transaction')
router.register('statements', StatementViewSet, basename='finance-statement')
router.register('fiscal-years', FiscalYearViewSet, basename='finance-fiscal-year')
urlpatterns = [
    path('summary/', SummaryView.as_view()),
    path('projects/', ProjectOptionsView.as_view()),
    path('reports/<str:name>/', ReportView.as_view()),
    path('export/', ExportView.as_view()),
    path('export/audit-pack/', ExportView.as_view(), {'pack': True}),
] + router.urls
