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
    path('login/', views.login, name='login'),
    path('post-login/', views.post_login_redirect, name="post_login_redirect"),
    path('courses/', views.courses, name='courses'),
    path('available_courses/<int:user_id>/',views.available_courses, name='available_courses'),
    path("payment/<int:user_id>/<int:course_id>/", views.payment, name="payment"), #payment
    path("stk/<int:user_id>/<int:course_id>/", views.stk, name="stk"), #stk push
    path("payment-status/<int:user_id>/<int:course_id>/", views.payment_status, name="payment_status"), #payment status
    path("check-status/<int:user_id>/<int:course_id>/<str:checkout_id>/", views.check_payment_status, name="check_payment_status"),
    path("mpesa/callback/", views.mpesa_callback, name="mpesa_callback"), # callback
    path('My courses/<int:user_id>/', views.enrolled_courses, name='mycourses'), #enrolled courses
    path("enrollment/<int:enrollment_id>/receipt/", views.enrollment_receipt, name="enrollment_receipt"), #Receipt
    path('main/', views.main, name='main-page'),
    path('contact/', views.contact, name='contact'),
    path('contacts/', views.contacts, name='contacts'),
    path('dashbord/', views.admin_dashboard, name='admin_dashboard'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('records/<int:user_id>', views.records, name='records'),
    path('add_student/<int:user_id>/', views.add_student, name='add_student'),
    path('updates/<int:id>', views.updates, name='updates'),
    path('delete/<int:id>/', views.delete_member, name='delete_member'),
    path('restore/<int:id>/', views.restore_member, name='restore_member'),
    path('delete_contact/<int:id>/', views.delete_contact, name='delete_contact'),
    path('logout/', views.logout_view, name='logout_view'),
    path('download/pdf/', generate_pdf, name='generate_pdf'),
    path('settings/', views.settings_view, name='settings'),
    path('delete_account/<int:id>', views.delete_account_view, name='delete_account'),
    #--------reset password---------
    path('reset-request/', views.reset_request, name='reset-request'),
    path('reset-password/<str:username>/', views.reset_password, name='reset-password'),
    path('student-main/', views.student_main, name='student-main'),
    path('admin-_main/', views.admin_main, name='admin-main'),
    path("edit_student/", views.edit_student, name="edit_student"),
    path('course_list/', views.course_list, name='course_list'),
    path("learning/<int:student_id>/<int:course_id>/", views.learning, name="learning"),
    path("courses/<int:user_id>/", views.mentor_courses, name="mentor_courses"),
    path("add_course/<int:user_id>/", views.add_course, name="add_course"),
    path("add_module", views.add_module, name="add_module"),
    path('course/<int:course_id>/modules/', views.get_course_modules, name='get_course_modules'),
    path('course/<int:course_id>/modules/', views.course_modules_view, name='course_modules'), 
    path("lessons/add/<int:module_id>/", views.add_lesson, name="add_lesson"),
    path("modules/<int:module_id>/lessons/", views.get_module_lessons, name="get_module_lessons"),
    path("lessons/<int:lesson_id>/download/", views.download_note, name="download_note"),

    # urls for profile-student
    path('profile/<int:studentinfo>/student', views.student_profile, name='student_profile'),
    path('profile/<int:id>/change-password/', views.change_password_s, name='change_password'),
    path('profile/<int:id>/delete/', views.delete_account_s, name='delete_account'),

    # urls for profile-mentor
    path('mentor/<int:admininfo>/profile', views.mentor_profile, name='mentor_profile'),
    path('mentor/<int:id>/change-password/', views.change_password_m, name='change-password'),
    path('mentor/<int:id>/delete/', views.delete_account_m, name='account'),

    #url for students
    path('registered-students/', views.registered_students, name='registered_students'),
     #contact message
    path('contact_messages/', views.contact_message, name='contact_messages'),
    
    #notification
    path('latest_messages', views.latest_messages, name='latest_messages'),

    # Manage Enrollments (mentor/admin view)
    path("manage_enrollments/", views.manage_enrollments, name="manage_enrollments"),
    path("enrollment/<int:enrollment_id>/approve/", views.approve_enrollment, name="approve_enrollment"),
    path("enrollment/<int:enrollment_id>/reject/", views.reject_enrollment, name="reject_enrollment"),
    # Print all Enrollments
    path("print-enrollments/", views.print_enrollments, name="print_enrollments"),
    
    ]




