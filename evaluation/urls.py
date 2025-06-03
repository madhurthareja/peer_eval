from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

urlpatterns=[
    path('', views.home, name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='evaluation/registration/login.html',extra_context={'is_home': True}),
        name='login'
    ),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('upload/', views.upload_students, name='upload_students'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('assignments/', views.assignment_dashboard, name='assignment_dashboard'),
    path('assignments/create/', views.create_assignment, name='create_assignment'),
    path('assignments/<int:pk>/edit/', views.edit_assignment, name='edit_assignment'),
    path('assignments/<int:pk>/delete/', views.delete_assignment, name='delete_assignment'),
    path('assignments/<int:pk>/submissions/', views.assignment_submissions, name='assignment_submissions'),
    path('assignments/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('students/', views.manage_students, name='manage_students'),
    path('help/', views.help, name='help'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('students/<int:student_id>/assignments/', views.student_assignments, name='student_assignments'),
    path('submissions/<int:submission_id>/delete/', views.delete_submission, name='delete_submission'),
    path('peer-reviews/', views.peer_review_dashboard, name='peer_review_dashboard'),
    path('peer-reviews/create/<int:assignment_id>/', views.create_peer_review_template, name='create_peer_review_template'),
    path('peer-reviews/distribute/<int:assignment_id>/', views.distribute_peer_reviews, name='distribute_peer_reviews'),
    path('peer-reviews/assigned/', views.assigned_peer_reviews, name='assigned_peer_reviews'),
    path('peer-reviews/fill/<int:review_id>/', views.fill_peer_review, name='fill_peer_review'),
    path('results/', views.manage_results, name='manage_results'),
    path('my-results/', views.my_results, name='my_results'),
    path('results/<int:assignment_id>/', views.assignment_results, name='assignment_results'),
    path('results/<int:assignment_id>/publish/', views.publish_results, name='publish_results'),
    path('results/<int:assignment_id>/unpublish/', views.unpublish_results, name='unpublish_results'),
    path('peer-reviews/edit/<int:template_id>/', views.edit_peer_review_template, name='edit_peer_review_template'),
    path('student/assignment/<int:assignment_id>/', views.student_assignment_detail, name='student_assignment_detail'),
    path('assignment/<int:assignment_id>/export/', views.export_review_results, name='export_review_results'),
    path('peer-reviews/delete/<int:review_id>/', views.delete_peer_review, name='delete_peer_review'),
    path('peer-reviews/revoke/<int:assignment_id>/', views.revoke_peer_review_distributions, name='revoke_peer_review_distributions'),
    path('peer-reviews/resend/<int:review_id>/', views.resend_for_evaluation, name='resend_for_evaluation'),
    path('user/<int:user_id>/update-password/', views.update_password, name='update_password'),
]

