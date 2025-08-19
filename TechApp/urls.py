from tkinter.font import names
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from TechApp import views
from .views import generate_pdf

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='index'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('register/', views.register, name='register'),
    path("verify-email/<slug:username>", views.verify_email, name="verify-email"),
    path("resend-otp", views.resend_otp, name="resend-otp"),
    path('login/', views.login, name='login'),
    path('courses/', views.courses, name='courses'),
    path('available_courses/<int:user_id>/',views.available_courses, name='available_courses'),
    path('payment/<int:user_id>/', views.payment, name='payment'),
    path('stk/', views.stk, name='stk'),
    path('token/', views.token, name='token'),
    path('main/', views.main, name='main-page'),
    path('contact/', views.contact, name='contact'),
    path('contacts/', views.contacts, name='contacts'),
    path('dashbord/', views.admin_dashboard, name='admin_dashboard'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('records/<int:user_id>', views.records, name='records'),
    path('add_student/<int:user_id>/', views.add_student, name='add_student'),
    path('updates/<int:id>', views.updates, name='updates'),
    path('delete/<int:id>/', views.delete_member, name='delete_member'),
    path('restore/<int:id>/', views.restore_member, name='restore_member'),
    path('delete_contact/<int:id>/', views.delete_contact, name='delete_contact'),
    path('logout_student/', views.logout_student, name='logout_student'),
    path('logout_mentor/', views.logout_mentor, name='logout_mentor'),
    path('download/pdf/', generate_pdf, name='generate_pdf'),
    path('profile_update/<int:user_id>', views.profile_update, name='profile_update'),
    path('settings/', views.settings_view, name='settings'),
    path('delete_account/<int:id>', views.delete_account_view, name='delete_account'),
    path('add_cours/', views.add_cours, name='add_cours'),
    path('student_assignments/',views.student_assignments, name='student_assignments'),
    path('mentor_viewstatus/', views.mentor_viewstatus, name='mentor_viewstatus'),
    path('reset-request/', views.reset_request, name='reset-request'),
    path('reset-password/<str:username>/', views.reset_password, name='reset-password'),
    path('resent_reset_otp/', views.resend_reset_otp, name='resend-reset-otp'),
    path('admin_reset_request/', views.admin_reset_request, name='admin-reset-request'),
    path('admin_reset_password/<str:username>/', views.admin_reset_password, name='admin-reset-password'),
    path('admin_resend_reset_otp/', views.admin_resend_reset_otp, name='admin-resend-reset-otp'),
    path('user-profile/<int:user_id>/',views.user_profile, name='user-profile'),
    path('student-main/', views.student_main, name='student-main'),
    path('edit_profile/<int:user_id>', views.edit_profile, name='edit_profile'),
    path('users-profile/<int:user_id>/', views.users_profile, name='users-profile'),
    path('admin-_main/', views.admin_main, name='admin-main'),
    path("edit_student/", views.edit_student, name="edit_student"),
    path('enroll-course/', views.enroll_course, name='enroll_course'),
    path('course_list/', views.course_list, name='course_list'),
    path("learning/<int:studentinfo>/", views.learning, name="learning"),
    path("courses/<int:user_id>/", views.mentor_courses, name="mentor_courses"),
    path("add_course/<int:user_id>/", views.add_course, name="add_course"),
    path("modules/add/", views.add_module, name="add_module"),
    path("lessons/add/", views.add_lesson, name="add_lesson"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    ]




