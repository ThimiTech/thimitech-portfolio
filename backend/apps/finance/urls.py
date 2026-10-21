from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MyPayslipViewSet, SalaryViewSet, PayslipViewSet, ExpenseViewSet, InvoiceViewSet, SummaryView
router = DefaultRouter()
router.register('my-payslips', MyPayslipViewSet, basename='finance-my-payslip')
router.register('salaries', SalaryViewSet, basename='finance-salary')
router.register('payslips', PayslipViewSet, basename='finance-payslip')
router.register('expenses', ExpenseViewSet, basename='finance-expense')
router.register('invoices', InvoiceViewSet, basename='finance-invoice')
urlpatterns = [path('summary/', SummaryView.as_view())] + router.urls
