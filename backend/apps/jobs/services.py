"""Hiring side effects: telling the applicant where they stand, and turning one into an employee."""
from django.db import transaction
from django.utils import timezone

from apps.leave.services import hr_users, notify
from apps.notifications.services import push
from apps.org.onboarding import start_onboarding

STATUS_MESSAGE = {
    'shortlisted': 'Good news: your application has been shortlisted. We will be in touch about next steps.',
    'interview': 'We would like to interview you. Someone from our team will contact you to arrange a time.',
    'selected': 'Congratulations: you have been selected. We will contact you with the details of your offer.',
    'rejected': 'Thank you for your interest. We will not be moving forward with your application this time.',
}


def announce_status(application):
    """Email the applicant when their application moves to a stage they should hear about."""
    message = STATUS_MESSAGE.get(application.status)
    if message:
        notify(f'Your application for {application.job.title}', f'Hi {application.name},\n\n{message}\n\nThimi Tech',
               [application.applicant])


def announce_new(application):
    push(hr_users(), 'job_application', f'{application.name} applied for {application.job.title}',
         link=f'/app/hiring?application={application.pk}', exclude=application.applicant)


@transaction.atomic
def hire(application, *, department=None, designation='', employment_type=None, join_date=None):
    """Applicant becomes staff: guest -> employee (higher roles are left alone), profile filled from the
    application, onboarding checklist started. Returns the user."""
    user = application.applicant
    if not user.has_role('employee'):
        user.role = user.Role.EMPLOYEE
        if not (user.first_name or user.last_name):
            user.first_name, _, user.last_name = application.name.partition(' ')
        user.save()  # org signal creates the EmployeeProfile
    profile = user.profile
    profile.designation = designation or profile.designation or application.job.title
    profile.department = department or profile.department
    profile.employment_type = employment_type or profile.employment_type
    profile.join_date = join_date or profile.join_date or timezone.localdate()
    profile.phone = profile.phone or application.phone
    profile.address = profile.address or application.address
    profile.save()
    if application.status != 'selected':
        application.status = 'selected'
        application.save(update_fields=['status', 'updated_at'])
    start_onboarding(user)
    push([user], 'hired', 'Welcome to the team', 'Your workspace is ready. Start with your onboarding checklist.',
         '/app/profile')
    return user
