import json
import logging
from django.http import FileResponse
from django.db import transaction
from django.utils import timezone
import requests
from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
from django.db.models import Q 
from datetime import timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.db.models import Prefetch
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from requests.auth import HTTPBasicAuth
from django.contrib.auth import authenticate, login as auth_login
from TechApp.credentials import MpesaAccessToken, LipanaMpesaPpassword
from django.shortcuts import  redirect,render, get_object_or_404
from django.contrib.auth import logout, authenticate
from django.contrib import messages
from TechApp.forms import  StudentForm,StudentEditForm, MentorEditForm,AdminForm, CourseForm, ModuleForm, LessonForm
from TechApp.models import Course, Member, Enrollment,LessonProgress, Contact, AdminLogin,Module, Lesson,Topic, Subtopic
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import random
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white, darkblue, lightgrey
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import os
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)

#home page
def home(request):
    return render(request, 'index.html')

#about page
def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))

#student registration view
def register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        id_number = request.POST.get('id_number')
        date_of_birth = request.POST.get('date')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        confirm_password = request.POST.get('c_password')
        profile_image = request.FILES.get('profile_image')

        # Validate uniqueness
        if Member.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken.")
            return redirect('register')
        if Member.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('register')
        if Member.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number is already taken.")
            return redirect('register')
        if Member.objects.filter(id_number=id_number).exists():
            messages.error(request, "ID number is already taken.")
            return redirect('register')

        # Validate password match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        # Create user
        new_user = Member(
            name=name,
            email=email,
            username=username,
            phone=phone,
            id_number=id_number,
            date_of_birth=date_of_birth,
            gender=gender,
            password=make_password(password),
            profile_image=profile_image,
            is_active=False,  # Keep the user inactive until OTP verification
        )
        new_user.save()

        # Generate OTP and send email
        new_user.generate_otp()
        new_user.refresh_from_db()  # Ensure the OTP is saved before sending email

        subject = "Email Verification"
        message = f"""
            Hi {new_user.username}, here is your OTP: {new_user.otp_code} 
            It expires in 3 minutes. Click below to verify your email:
            http://127.0.0.1:8000/verify-email/{new_user.username}
        """
        sender = "wekesabramuel00@gmail.com"
        receiver = [new_user.email]

        send_mail(subject, message, sender, receiver, fail_silently=False)

        messages.success(request, "Account created successfully! An OTP has been sent to your email.")
        return redirect("verify-email", username=new_user.username)

    return render(request, 'register.html')

def verify_email(request, username):
    user = get_object_or_404(Member, username=username)

    if request.method == 'POST':
        otp_input = request.POST.get('otp_code')

        if user.verify_otp(otp_input):  # Call verify_otp method
            messages.success(request, "Account activated successfully! You can now log in.")
            return redirect("login")
        else:
            messages.warning(request, "Invalid or expired OTP. Please try again.")
            return redirect("verify-email", username=user.username)

    return render(request, "verify_token.html")


def resend_otp(request):
    if request.method == 'POST':
        user_email = request.POST.get("otp_email")

        user = Member.objects.filter(email=user_email).first()

        if user:
            user.generate_otp()

            # Send email
            subject = "Email Verification"
            message = f"""
                Hi {user.username}, here is your new OTP: {user.otp_code} 
                It expires in 3 minutes. Click below to verify:
                http://127.0.0.1:8000/verify-email/{user.username}
            """
            sender = "wekesabramuel00@gmail.com"
            receiver = [user.email]

            send_mail(subject, message, sender, receiver, fail_silently=False)

            messages.success(request, "A new OTP has been sent to your email.")
            return redirect("verify-email", username=user.username)
        else:
            messages.error(request, "Email does not exist.")
            return redirect("resend-otp")

    return render(request, "resend_otp.html")


def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            student = Member.objects.get(username=username)
        except Member.DoesNotExist:
            messages.error(request, "Invalid username or password.")
            return redirect('/login')

        # Use check_password to verify the hashed password
        if check_password(password, student.password):
            request.session['username'] = username
            return redirect('student_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('/login')

    return render(request, 'login.html')

# student_dashboard
def student_dashboard(request):
    username = request.session.get('username')
    
    if not username:
        return redirect('login')

    try:
        studentinfo = Member.objects.get(username=username)
    except Member.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    # ✅ Get all enrollments for this student
    enrolled_courses = Enrollment.objects.filter(student=studentinfo)

    # ✅ Count totals
    enrolled_courses_count = enrolled_courses.count()  # all (pending + approved + rejected)
    active_courses_count = enrolled_courses.filter(status="Approved").count()  # only approved

    # ✅ Get all mentors
    mentors = AdminLogin.objects.all()

    context = {
        'studentinfo': studentinfo,
        'mentors': mentors,
        'enrolled_courses': enrolled_courses,
        'enrolled_courses_count': enrolled_courses_count,
        'active_courses_count': active_courses_count,
    }

    return render(request, 'student_dashboard.html', context)


#logout
def logout_student(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Get the admin info by username
        admininfo = AdminLogin.objects.filter(username=username).first()

        if admininfo and check_password(password, admininfo.password):
            request.session['username'] = username
            request.session['admin_id'] = admininfo.id

            messages.success(request, "Login successful! Welcome to the admin dashboard.")  
            return redirect('admin_dashboard')

        # Superuser login via Django’s auth
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            auth_login(request, user)
            messages.success(request, "Login successful! Redirecting to admin panel.")  
            return redirect('/admin/')

        # If nothing matched
        messages.error(request, "Invalid username or password")

    return render(request, 'mentor_login.html')

def admin_dashboard(request):
    username = request.session.get('username')
    if not username:
        return redirect('admin_login')

    try:
        admininfo = AdminLogin.objects.get(username=username)
    except AdminLogin.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_login')

    # Students
    member = Member.objects.all()
    total_students = member.count()
    today = timezone.now().date()
    new_today = member.filter(created_at__date=today).count()

    # Courses
    courses = Course.objects.all()
    total_courses = courses.count()

    # courses added this week
    start_week = today - timedelta(days=today.weekday())  # Monday of this week
    new_this_week = courses.filter(created_at__date__gte=start_week).count()

    return render(request, 'admin_dashboard.html', {
        'admininfo': admininfo,
        'member': member,
        'total_students': total_students,
        'new_today': new_today,
        'total_courses': total_courses,
        'new_this_week': new_this_week,
    })

def logout_mentor(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('admin_login')

def courses(request):
        return render(request, 'login.html')


def main(request):
    return render(request, 'main.html')

def contact(request):
    return render(request, 'contact.html')


def reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if user exists
        user = Member.objects.filter(email=email).first()

        if user:
            # Generate new OTP
            user.generate_otp()

            # Send OTP via email
            subject = "Password Reset OTP"
            message = f"""
                Hi {user.username}, your password reset OTP is: {user.otp_code}
                It expires in 3 minutes. Click below link to reset your password:
                https://techcampus-k4qi.onrender.com/reset-password/{user.username}
            """
            sender = "wekesabramuel00@gmail.com"
            receiver = [user.email]

            send_mail(subject, message, sender, receiver, fail_silently=False)

            messages.success(request, "OTP has been sent to your email. Check your inbox.")
            return redirect("reset-password", username=user.username)
        else:
            messages.error(request, "Email does not exist.")
            return redirect("reset-request")

    return render(request, "reset_request.html")


def reset_password(request, username):
    user = get_object_or_404(Member, username=username)

    if request.method == "POST":
        otp_code = request.POST.get("otp_code")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Check OTP validity
        if not user.otp_code or not user.otp_expires_at:
            messages.error(request, "OTP is missing. Request a new one.")
            return redirect("reset-request")

        if user.otp_code != otp_code:
            messages.error(request, "Invalid OTP. Try again.")
            return redirect("reset-password", username=username)

        if user.otp_expires_at < timezone.now():
            messages.error(request, "OTP has expired. Request a new one.")
            return redirect("reset-request")

        # Check password confirmation
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset-password", username=username)

        # Update password and clear OTP
        user.password = make_password(new_password)  # Hash the password
        user.otp_code = None  # Clear OTP after successful reset
        user.otp_expires_at = None
        user.save()

        messages.success(request, "Password reset successful! You can now log in.")
        return redirect("login")

    return render(request, "reset_password.html", {"username": username})


def resend_reset_otp(request):
    if request.method == 'POST':
        user_email = request.POST.get("otp_email")

        user = Member.objects.filter(email=user_email).first()

        if user:
            user.generate_otp()

            # Send new OTP via email
            subject = "Resend Password Reset OTP"
            message = f"""
                Hi {user.username}, your new OTP is: {user.otp_code}
                It expires in 3 minutes. Click below to reset your password:
                http://127.0.0.1:8000/reset-password/{user.username}
            """
            sender = "wekesabramuel00@gmail.com"
            receiver = [user.email]

            send_mail(subject, message, sender, receiver, fail_silently=False)

            messages.success(request, "A new OTP has been sent to your email.")
            return redirect("reset-password", username=user.username)
        else:
            messages.error(request, "Email does not exist.")
            return redirect("resend-reset-otp")

    return render(request, "resent_reset_otp.html")


#add student
def add_student(request, user_id):
    admininfo = get_object_or_404(AdminLogin, id=user_id)  # Fetch the admin info

    if request.method == 'POST':
        # Extracting form data
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        id_number = request.POST.get('id_number')
        date_of_birth = request.POST.get('date')
        gender = request.POST.get('gender')

        # Validation for unique fields
        if Member.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken.")
            return redirect('add_student', user_id=user_id)
        elif Member.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('add_student', user_id=user_id)
        elif Member.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number is already taken.")
            return redirect('add_student', user_id=user_id)
        elif Member.objects.filter(id_number=id_number).exists():
            messages.error(request, "ID number is already taken.")
            return redirect('add_student', user_id=user_id)

        # Default password setup (hashed)
        default_password = "student1234"
        hashed_password = make_password(default_password)

        # Save student
        student = Member(
            name=name,
            username=username,
            email=email,
            phone=phone,
            id_number=id_number,
            date_of_birth=date_of_birth,
            gender=gender,
            password=hashed_password,
        )
        student.save()

        messages.success(request, "Student added successfully with default password: student1234")
        return redirect('admin_dashboard')  # Pass user_id to the 'records' URL

    return render(request, 'add_student.html', {'admininfo': admininfo})

def delete_account_view(request, id):
    studentinfo = get_object_or_404(Member, id=id)
    studentinfo.delete()

    messages.success(request, "Account Deleted Successfully")  # Success message

    return redirect('register')

# available courses
def available_courses(request, user_id):
    studentinfo = get_object_or_404(Member, id=user_id)
    courses = Course.objects.select_related("mentor").all()

    # get enrolled course IDs for this student
    enrolled_ids = Enrollment.objects.filter(
        student=studentinfo
    ).values_list("course_id", flat=True)

    return render(request, 'available_courses.html', {
        'studentinfo': studentinfo,
        'courses': courses,
        'enrolled_ids': set(enrolled_ids),  # pass set for fast lookup
    })


# Payment form
def payment(request, user_id, course_id):
    studentinfo = get_object_or_404(Member, id=user_id)
    course = get_object_or_404(Course, id=course_id)

    # ✅ Check if enrollment already exists
    existing_enrollment = Enrollment.objects.filter(
        student=studentinfo, course=course,
    ).first()

    if existing_enrollment:
    # Fetch all enrollments for consistency
       enrollments = Enrollment.objects.filter(student=studentinfo).select_related("course")
    
       return render(request, "enrolled_courses.html", {
        "studentinfo": studentinfo,
        "enrollments": enrollments,
        "message": f"You are already enrolled in {course.title}."
       })

    # If not enrolled, continue to payment page
    return render(request, "payment.html", {
        "studentinfo": studentinfo,
        "course": course,
        "user_id": user_id,
        "course_id": course_id
    })

# enrolled courses
def enrolled_courses(request, user_id):
    studentinfo = get_object_or_404(Member, id=user_id)

    # ✅ only approved enrollments
    enrollments = Enrollment.objects.filter(
        student=studentinfo, status="approved"
    ).select_related("course")

    return render(request, 'enrolled_courses.html', {
        'studentinfo': studentinfo,
        'enrollments': enrollments
    })

#learning view
def learning(request, student_id, course_id):
    student = get_object_or_404(Member, id=student_id)
    course = get_object_or_404(Course, id=course_id)

    enrollment = Enrollment.objects.filter(
        student=student, course=course, status="approved"
    ).first()

    if not enrollment:
        return render(request, "available_courses.html", {
            "course": course, 
            "student": student
        })

    modules = course.modules.prefetch_related("topics__subtopics", "lessons").all()

    # Calculate progress for each module and lesson
    for module in modules:
        total_lessons = module.lessons.count()

        # ✅ count completed lessons using LessonProgress
        completed_lessons = LessonProgress.objects.filter(
            lesson__module=module,
            student=student,
            completed=True
        ).count()

        module.progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        module.is_completed = completed_lessons == total_lessons
        module.is_accessible = True  # (add logic later if you want to lock)

        # ✅ attach lesson-level progress
        for lesson in module.lessons.all():
            progress = LessonProgress.objects.filter(
                lesson=lesson, student=student, completed=True
            ).first()
            lesson.is_completed = bool(progress)
            lesson.is_accessible = True  # (customize if needed)
            lesson.is_current = False    # could mark one as "current"

    # Calculate enrollment (course-level) progress
    total_modules = modules.count()
    completed_modules = sum(1 for module in modules if module.is_completed)

    enrollment.progress_percentage = (completed_modules / total_modules * 100) if total_modules > 0 else 0
    enrollment.completed_modules_count = completed_modules

    return render(request, "learning_page.html", {
        "student": student,
        "studentinfo": student,
        "course": course,
        "modules": modules,
        "enrollment": enrollment,
    })

# STK push - Add more logging
def stk(request, user_id, course_id):
    student = get_object_or_404(Member, id=user_id)
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        phone = request.POST.get("phone")
        amount = int(float(course.amount)) if course.amount else 1
        
        logger.info(f"=== STK PUSH INITIATED ===")
        logger.info(f"Student: {student.id}, Course: {course.id}, Amount: {amount}, Phone: {phone}")

        # Get access token
        access_token = MpesaAccessToken.get_access_token()
        
        if not access_token:
            error_msg = "Failed to get M-Pesa access token. Check your credentials."
            logger.error(error_msg)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            else:
                messages.error(request, error_msg)
                return redirect("payment", user_id=student.id, course_id=course.id)

        # Get password details
        password_data = LipanaMpesaPpassword.get_password()
        if not password_data:
            error_msg = "Failed to generate M-Pesa password."
            logger.error(error_msg)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            else:
                messages.error(request, error_msg)
                return redirect("payment", user_id=student.id, course_id=course.id)

        # Build callback                      

        if settings.DEBUG:
            callback_url = f"http://localhost:8000/mpesa/callback/?student_id={student.id}&course_id={course.id}"
        else:
            callback_url = f"https://techcampus-r82w.onrender.com/mpesa/callback/?student_id={student.id}&course_id={course.id}"

        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        payment_request = {
            "BusinessShortCode": password_data['business_shortcode'],
            "Password": password_data['password'],
            "Timestamp": password_data['timestamp'],
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": password_data['business_shortcode'],
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": f"SirBrams Tech Virtual Campus.For Name: {student.name}| Student No: {student.student_number} | Course: {course.title}",
            "TransactionDesc": f"Payment for {course.title}-{course.code}",
        }

        logger.info(f"Payment request prepared for phone: {phone}")

        try:
            response = requests.post(api_url, json=payment_request, headers=headers, timeout=30)
            logger.info(f"STK Push HTTP Status: {response.status_code}")
            
            # Check if response is valid JSON
            try:
                response_data = response.json()
                logger.info(f"STK Push API Response: {response_data}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {response.text}")
                error_msg = "Invalid response from M-Pesa. Please try again."
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_msg}, status=500)
                else:
                    messages.error(request, error_msg)
                return redirect("payment", user_id=student.id, course_id=course.id)

            # ✅ FIXED: Properly check for success
            checkout_id = response_data.get("CheckoutRequestID") or response_data.get("checkoutRequestID")
            response_code = response_data.get("ResponseCode") or response_data.get("responseCode")
            response_description = response_data.get('ResponseDescription') or response_data.get('responseDescription') or ''
            error_message = response_data.get('errorMessage') or response_data.get('error_message') or ''

            # ✅ SUCCESS CONDITIONS: ResponseCode 0 OR success message
            is_success = (
                response_code == 0 or 
                "success" in response_description.lower() or
                "request accepted for processing" in response_description.lower()
            )

            if is_success and checkout_id:
                # Store session data
                request.session["checkout_id"] = checkout_id
                request.session["stk_student_id"] = user_id
                request.session["stk_course_id"] = course_id
                request.session["stk_timestamp"] = str(timezone.now())
                request.session["stk_phone"] = phone
                request.session["stk_amount"] = amount
                
                logger.info(f"✅ STK Push Successful - CheckoutID: {checkout_id}")
                logger.info(f"✅ Response Description: {response_description}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': 'Payment initiated successfully! Check your phone to complete the payment.',
                        'redirect_url': reverse('payment_status', kwargs={'user_id': user_id, 'course_id': course_id})
                    })
                else:
                    return redirect("payment_status", user_id=user_id, course_id=course_id)
            else:
                # ✅ IMPROVED ERROR HANDLING
                logger.error(f"❌ STK Push Failed")
                logger.error(f"❌ Response Code: {response_code}")
                logger.error(f"❌ Response Description: {response_description}")
                logger.error(f"❌ Error Message: {error_message}")
                logger.error(f"❌ Full response: {response_data}")
                
                # User-friendly error messages
                if "insufficient" in error_message.lower() or "insufficient" in response_description.lower():
                    user_error_msg = "Insufficient balance in your M-Pesa account."
                elif "timeout" in error_message.lower():
                    user_error_msg = "Payment request timed out. Please try again."
                elif "invalid" in error_message.lower() or "invalid" in response_description.lower():
                    user_error_msg = "Invalid phone number or transaction details."
                elif "cancelled" in error_message.lower() or "cancelled" in response_description.lower():
                    user_error_msg = "Payment was cancelled. Please try again."
                else:
                    user_error_msg = f"Payment initiation failed: {response_description or error_message or 'Unknown error'}"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': user_error_msg}, status=400)
                else:
                    messages.error(request, user_error_msg)
                
        except requests.exceptions.Timeout:
            logger.error("❌ STK Push request timed out")
            error_msg = "Payment request timed out. Please try again."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            else:
                messages.error(request, error_msg)
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ STK Push connection error")
            error_msg = "Network connection error. Please check your internet and try again."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            else:
                messages.error(request, error_msg)
                
        except Exception as e:
            logger.error(f"❌ STK Push Exception: {str(e)}")
            error_msg = "An unexpected error occurred. Please try again."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            else:
                messages.error(request, error_msg)

        return redirect("payment", user_id=student.id, course_id=course.id)

    return render(request, "payment.html", {"student": student, "course": course})

#payment status
def payment_status(request, user_id, course_id):
    studentinfo = get_object_or_404(Member, id=user_id)
    course = get_object_or_404(Course, id=course_id)
    
    # Pass debug mode to template
    debug = settings.DEBUG

    return render(request, "payment_status.html", {
        "studentinfo": studentinfo,
        "user_id": studentinfo.id,
        "course": course,
        "course_id": course.id,
        "checkout_id": request.session.get("checkout_id"),
        "debug": debug,  # Pass debug flag to template
    })

#check payment status
def check_payment_status(request, user_id, course_id, checkout_id):
    """Check payment status with multiple verification methods"""
    logger.info(f"=== STATUS CHECK ===")
    logger.info(f"User: {user_id}, Course: {course_id}, Checkout: {checkout_id}")
    
    student = get_object_or_404(Member, id=user_id)
    course = get_object_or_404(Course, id=course_id)

    # Method 1: Check Enrollment by checkout_id (primary method)
    enrollment = Enrollment.objects.filter(
        checkout_request_id=checkout_id,
        status__in=["paid", "approved", "paid_pending_approval"]
    ).first()
    
    if enrollment:
        logger.info(f"✅ Enrollment found via checkout_id - SUCCESS: {enrollment.id}")
        return JsonResponse({"status": "success", "enrollment_id": enrollment.id})

    # Method 2: Check Enrollment by student/course (fallback)
    enrollment = Enrollment.objects.filter(
        student=student,
        course=course,
        status__in=["paid", "approved", "paid_pending_approval"]
    ).first()
    
    if enrollment:
        logger.info(f"✅ Enrollment found via student/course - SUCCESS: {enrollment.id}")
        # Update with checkout_id if missing
        if not enrollment.checkout_request_id:
            enrollment.checkout_request_id = checkout_id
            enrollment.save()
        return JsonResponse({"status": "success", "enrollment_id": enrollment.id})

    # Method 3: Local testing - auto-complete after 30 seconds
    if settings.DEBUG:
        stk_timestamp = request.session.get("stk_timestamp")
        if stk_timestamp:
            try:
                stk_time = timezone.datetime.fromisoformat(stk_timestamp)
                elapsed = timezone.now() - stk_time
                
                if elapsed.total_seconds() > 30:
                    logger.info("🧪 LOCAL TESTING: Auto-completing payment after 30 seconds")
                    enrollment, created = Enrollment.objects.update_or_create(
                        student=student,
                        course=course,
                        defaults={
                            "mentor_name": getattr(course.mentor, 'name', '') if hasattr(course, 'mentor') and course.mentor else "",
                            "student_name": student.name,
                            "course_title": course.title,
                            "course_code": course.code,
                            "amount": course.amount,
                            "duration": getattr(course, 'duration', ''),
                            "checkout_request_id": checkout_id,
                            "status": "paid",
                        }
                    )
                    logger.info(f"🧪 Enrollment {'created' if created else 'updated'}: {enrollment.id}")
                    return JsonResponse({"status": "success", "enrollment_id": enrollment.id, "debug": True})
            except Exception as e:
                logger.error(f"Local testing error: {e}")

    # Method 4: Check if payment was recently made (within last 10 minutes)
    recent_enrollment = Enrollment.objects.filter(
        student=student,
        course=course,
        created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
    ).first()
    
    if recent_enrollment:
        logger.info(f"🕒 Recent enrollment found - marking as paid: {recent_enrollment.id}")
        recent_enrollment.status = "paid"
        recent_enrollment.checkout_request_id = checkout_id
        recent_enrollment.save()
        return JsonResponse({"status": "success", "enrollment_id": recent_enrollment.id})

    logger.info("⏳ Payment still pending")
    return JsonResponse({"status": "pending"})


#mpesa_callback view
from django.core.mail import send_mail
from django.conf import settings

@csrf_exempt
def mpesa_callback(request):
    """Process M-Pesa callback"""
    logger.info("=== MPESA CALLBACK RECEIVED ===")
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
        logger.info(f"Callback payload: {json.dumps(payload, indent=2)}")
        
        stk_callback = payload.get('Body', {}).get('stkCallback', {})
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode', 1)
        result_desc = stk_callback.get('ResultDesc', '')
        
        logger.info(f"Callback - CheckoutID: {checkout_id}, ResultCode: {result_code}, Desc: {result_desc}")
        
        # Get student/course from query params or AccountReference
        student_id = request.GET.get('student_id')
        course_id = request.GET.get('course_id')
        
        if not student_id or not course_id:
            items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in items:
                if item.get('Name') == 'AccountReference':
                    account_ref = item.get('Value', '')
                    if '|' in account_ref:
                        student_id, course_id = account_ref.split('|')
                        break
        
        if student_id and course_id:
            student = Member.objects.get(id=int(student_id))
            course = Course.objects.get(id=int(course_id))
            
            if result_code == 0:
                items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                mpesa_receipt = None
                amount = None
                
                for item in items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt = item.get('Value')
                    elif item.get('Name') == 'Amount':
                        amount = item.get('Value')
                
                enrollment, created = Enrollment.objects.update_or_create(
                    student=student,
                    course=course,
                    defaults={
                        "mentor_name": getattr(course.mentor, 'name', '') if course.mentor else "",
                        "student_name": student.name,
                        "course_title": course.title,
                        "course_code": course.code,
                        "amount": amount or course.amount,
                        "duration": getattr(course, 'duration', ''),
                        "checkout_request_id": checkout_id,
                        "transaction_code": mpesa_receipt or "",
                        "status": "paid",
                    }
                )
                logger.info(f"✅ Enrollment {'created' if created else 'updated'}: {enrollment.id}")

                # ✅ Send Email Notifications
                subject = f"Payment Successful - {course.title}"
                student_message = (
                    f"Hello {student.name},\n\n"
                    f"Your payment of KES {amount} for '{course.title}' was successful. "
                    f"Receipt No: {mpesa_receipt}.\n\n"
                    "You are now enrolled. Wait for Mentor to Approve. 🎉\n\n"
                    "Best regards,\nSirBrams Tech Virtual Campus"
                )
                mentor_message = (
                    f"Hello {course.mentor.name if course.mentor else 'Mentor'},\n\n"
                    f"{student.name} has successfully enrolled in '{course.title}'.\n"
                    f"Payment Receipt: {mpesa_receipt}, Amount: KES {amount}.\n\n"
                    "Please check your dashboard to approve the course.\n\n"
                    "Best regards,\nSirBrams Tech Virtual Campus"
                )

                try:
                    # Send to student
                    if student.email:
                        send_mail(subject, student_message, settings.DEFAULT_FROM_EMAIL, [student.email])
                    
                    # Send to mentor (if email exists)
                    if getattr(course.mentor, 'email', None):
                        send_mail(subject, mentor_message, settings.DEFAULT_FROM_EMAIL, [course.mentor.email])
                except Exception as e:
                    logger.error(f"❌ Email sending failed: {e}")

            else:
                logger.warning(f"❌ Payment failed: {result_desc}")
        
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
        
    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


#receipt
def enrollment_receipt(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

    # PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="receipt_{enrollment.transaction_code or enrollment.id}.pdf"'

    # Setup PDF
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Colors
    primary_color = Color(0.2, 0.4, 0.6)  # Dark blue
    accent_color = Color(0.9, 0.1, 0.1)   # Red for important info
    header_color = Color(0.95, 0.95, 0.95)  # Light grey for headers

    # Add logo (replace with your logo path)
    try:
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'asset','img', 'logo.png')
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)
            p.drawImage(logo, 50, height - 80, width=60, height=60, mask='auto')
    except:
        pass  # Continue without logo if not found

    # Header Section
    p.setFillColor(primary_color)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(130, height - 50, "SirBrams Tech Virtual Campus")
    
    p.setFillColor(black)
    p.setFont("Helvetica", 10)
    p.drawString(130, height - 70, "123 Tech Street, Nairobi, Kenya")
    p.drawString(130, height - 82, "Phone: +254 742 524 370 | Email: sirbrams.b@gmail.com")

    # Receipt Title
    p.setFillColor(accent_color)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(width / 2, height - 120, "PAYMENT RECEIPT")
    
    # Receipt Number and Date
    p.setFillColor(black)
    p.setFont("Helvetica", 10)
    p.drawString(width - 200, height - 140, f"Receipt No: RCPT{enrollment.id:06d}")
    p.drawString(width - 200, height - 155, f"Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}")

    # Main content box
    p.setStrokeColor(lightgrey)
    p.setLineWidth(1)
    p.rect(40, height - 400, width - 80, 280, stroke=1, fill=0)

    # Student Information Section
    y = height - 180
    p.setFillColor(header_color)
    p.rect(50, y - 25, width - 100, 25, stroke=0, fill=1)
    
    p.setFillColor(primary_color)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(60, y - 18, "STUDENT INFORMATION")

    p.setFillColor(black)
    p.setFont("Helvetica", 11)
    y -= 45
    p.drawString(60, y, f"Full Name:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.student_name}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Phone Number:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{getattr(enrollment.student, 'phone', 'N/A')}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Student ID:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"STU{enrollment.student.id:05d}")

    # Payment Details Section
    y -= 40
    p.setFillColor(header_color)
    p.rect(50, y - 25, width - 100, 25, stroke=0, fill=1)
    
    p.setFillColor(primary_color)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(60, y - 18, "PAYMENT DETAILS")

    p.setFillColor(black)
    p.setFont("Helvetica", 11)
    y -= 45
    p.drawString(60, y, f"Course Title:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.course_title}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Course Code:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.course_code}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Mentor:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.mentor_name}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Duration:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.duration or 'Not specified'}")

    # Transaction Details Section
    y -= 40
    p.setFillColor(header_color)
    p.rect(50, y - 25, width - 100, 25, stroke=0, fill=1)
    
    p.setFillColor(primary_color)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(60, y - 18, "TRANSACTION INFORMATION")

    p.setFillColor(black)
    p.setFont("Helvetica", 11)
    y -= 45
    p.drawString(60, y, f"Transaction ID:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.transaction_code or 'Pending'}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Payment Date:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.created_at.strftime('%B %d, %Y at %H:%M')}")
    
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Payment Status:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(150, y, f"{enrollment.status.upper()}")

    # Amount Section (Highlighted)
    y -= 40
    p.setFillColor(accent_color)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(60, y, f"TOTAL AMOUNT PAID:")
    p.drawString(width - 150, y, f"KES {enrollment.amount:,.2f}")

    # Footer Section
    p.setFillColor(lightgrey)
    p.rect(40, 30, width - 80, 60, stroke=0, fill=1)
    
    p.setFillColor(black)
    p.setFont("Helvetica-Oblique", 9)
    p.drawCentredString(width / 2, 70, "This is an official receipt from SirBrams Tech Virtual campus")
    p.drawCentredString(width / 2, 55, "For any inquiries, please contact: sirbrams.b@gmail.com | +254 742 524 370")
    p.drawCentredString(width / 2, 40, "Thank you for choosing SirBrams Tech Virtual Campus!")

    # Add watermark for completed payments
    if enrollment.status == 'completed':
        p.setFillColor(Color(0.9, 0.9, 0.9, alpha=0.3))  # Light grey with transparency
        p.setFont("Helvetica-Bold", 60)
        p.rotate(45)
        p.drawString(250, -150, "PAID")
        p.rotate(-45)  # Reset rotation

    p.showPage()
    p.save()
    return response

#mentor Actions for student payments and enrollments
def manage_enrollments(request):
    admininfo = get_object_or_404(AdminLogin, id=request.session.get("admin_id"))


    search_query = request.GET.get("q", "")

    # Filter enrollments with student + course details
    enrollments = Enrollment.objects.select_related("student", "course").filter(course__mentor=admininfo)

    if search_query:
        enrollments = enrollments.filter(
            Q(student__name__icontains=search_query) |
            Q(student__phone__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(course__code__icontains=search_query) |
            Q(transaction_code__icontains=search_query) |   # ✅ match your Enrollment field
            Q(status__icontains=search_query)
        )

    # Paginate (10 per page)
    paginator = Paginator(enrollments, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "admininfo":admininfo
    }
    return render(request, "manage_enrollments.html", context)


# ✅ Approve Enrollment
def approve_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    enrollment.status = "approved"
    enrollment.save()

    # ✅ Send email to student
    subject = "Course Enrollment Approved"
    message = (
        f"Hello {enrollment.student.name},\n\n"
        f"Your enrollment for the course '{enrollment.course.title}' has been approved. 🎉\n"
        "You can now start learning.\n\n"
        "Best regards,\nSirBrams Tech Virtual Campus"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [enrollment.student.email])

    messages.success(request, f"{enrollment.student.name}'s enrollment approved.")
    return redirect("manage_enrollments")


# ✅ Reject Enrollment
def reject_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    enrollment.status = "rejected"
    enrollment.save()

    # ✅ Send email to student
    subject = "Course Enrollment Rejected"
    message = (
        f"Hello {enrollment.student.name},\n\n"
        f"Unfortunately, your enrollment for the course '{enrollment.course.title}' "
        "has been rejected. Please contact support for further assistance.\n\n"
        "Best regards,\nSirBrams Tech Virtual Campus"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [enrollment.student.email])

    messages.error(request, f"{enrollment.student.name}'s enrollment rejected.")
    return redirect("manage_enrollments")

 #print  
from django.template.loader import render_to_string
def print_enrollments(request):
    admininfo = get_object_or_404(AdminLogin, id=request.session.get("admin_id"))
    enrollments = Enrollment.objects.select_related("student", "course").filter(course__mentor=admininfo)
    # ✅ Total amount from all enrollments
    total_amount = enrollments.aggregate(total=Sum("amount"))["total"] or 0
    # ✅ Count of approved enrollments (active courses)
    approved_count = enrollments.filter(status="approved").count()
    # ✅ Count of rejected enrollments
    rejected_count = enrollments.filter(status="rejected").count()
    # ✅ Unique students across enrollments
    total_student_count = enrollments.values("student").distinct().count()
    context = {
        "enrollments": enrollments,
        "total_amount": total_amount,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "total_student_count": total_student_count,
        "admininfo":admininfo,
    }

    html = render_to_string("print_enrollments.html", context)
    return HttpResponse(html)  # Browser print dialog will work
   
 #records   
def records(request, user_id):
    allmembers = Member.objects.all()
    admininfo = get_object_or_404(AdminLogin, id=user_id)
    return render(request,'records.html',{'member':allmembers,'admininfo':admininfo})

#mentor update student info view
def updates(request, id):
    updatestudent = get_object_or_404(Member, id=id)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=updatestudent)
        if form.is_valid():
            form.save()
            messages.success(request, "Student information updated successfully!")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentForm(instance=updatestudent)

    return render(request, 'admin_dashboard.html', {'form': form, 'member_u': updatestudent})

def delete_member(request,id):
    member= Member.objects.get(id  = id )
    member.delete()
    return redirect('registered_students')

def records_view(request):
    members = Member.objects.filter(is_deleted=True)
    return render(request, 'records.html', {'members': members})

def restore_member(request, id):
    member = get_object_or_404(Member, id=id)
    member.restore()
    return redirect('/records')

def delete_contact(request, id):
    contacts = get_object_or_404(Contact, id=id)
    contacts.delete()
    return redirect('contact_messages')

def contacts(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')

        if name and email and message:  # ✅ validate required fields
            try:
                mycontact = Contact(
                    name=name,
                    email=email,
                    phone=phone,
                    message=message
                )
                mycontact.save()
                messages.success(request, "Your message has been sent successfully ✅")
            except Exception as e:
                messages.error(request, f"Failed to send message ❌: {str(e)}")
        else:
            messages.warning(request, "Please fill in all required fields.")

        return redirect('contacts')  # redirect after POST (best practice)

    return render(request, 'contact.html')

def generate_pdf(request):
    members = Member.objects.all()
    contacts = Contact.objects.all()

    context = {'member': members, 'allcontact': contacts}


    template_path = 'records.html'
    html = render_to_string(template_path, context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sirbrams_data.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had an error generating the PDF', status=500)
    return response


def admin_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if admin exists
        admin = AdminLogin.objects.filter(email=email).first()

        if admin:
            admin.generate_otp()

            # Send OTP via email
            subject = "Admin Password Reset OTP"
            message = f"""
                Hi {admin.username}, your password reset OTP is: {admin.otp_code}
                It expires in 3 minutes. Click below to reset your password:
                http://127.0.0.1:8000/admin-reset-password/{admin.username}
            """
            sender = "wekesabramuel00@gmail.com"
            receiver = [admin.email]

            send_mail(subject, message, sender, receiver, fail_silently=False)

            messages.success(request, "OTP has been sent to your email. Check your inbox.")
            return redirect("admin-reset-password", username=admin.username)
        else:
            messages.error(request, "Email does not exist.")
            return redirect("admin-reset-request")

    return render(request, "admin_reset_request.html")


def admin_reset_password(request, username):
    admin = get_object_or_404(AdminLogin, username=username)

    if request.method == "POST":
        otp_code = request.POST.get("otp_code")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validate OTP
        if not admin.otp_code or not admin.otp_expires_at:
            messages.error(request, "OTP is missing. Request a new one.")
            return redirect("admin-reset-request")

        if admin.otp_code != otp_code:
            messages.error(request, "Invalid OTP. Try again.")
            return redirect("admin-reset-password", username=username)

        if admin.otp_expires_at < timezone.now():
            messages.error(request, "OTP has expired. Request a new one.")
            return redirect("admin-reset-request")

        # Check password confirmation
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("admin-reset-password", username=username)

        # **Hash and save new password**
        admin.password = make_password(new_password)  # Hash the password before saving
        admin.otp_code = None  # Clear OTP after successful reset
        admin.otp_expires_at = None
        admin.save()

        messages.success(request, "Password reset successful! You can now log in.")
        return redirect("admin_login")

    return render(request, "admin_reset_password.html", {"username": username})


def admin_resend_reset_otp(request):
    if request.method == 'POST':
        admin_email = request.POST.get("otp_email")

        admin = AdminLogin.objects.filter(email=admin_email).first()

        if admin:
            admin.generate_otp()

            # Send new OTP via email
            subject = "Resend Admin Password Reset OTP"
            message = f"""
                Hi {admin.username}, your new OTP is: {admin.otp_code}
                It expires in 3 minutes. Click below to reset your password:
                http://127.0.0.1:8000/admin-reset-password/{admin.username}
            """
            sender = "wekesabramuel00@gmail.com"
            receiver = [admin.email]

            send_mail(subject, message, sender, receiver, fail_silently=False)

            messages.success(request, "A new OTP has been sent to your email.")
            return redirect("admin-reset-password", username=admin.username)
        else:
            messages.error(request, "Email does not exist.")
            return redirect("admin-resend-reset-otp")

    return render(request, "admin_resend_reset_otp.html")

def settings_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "You need to log in to access settings.")
        return redirect("login")

    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        user = Member.objects.get(username=request.user.username)

        # Check if current password is correct
        if not check_password(current_password, user.password):
            messages.error(request, "Current password is incorrect.")
            return redirect("settings")

        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("settings")

        # Update password
        user.password = make_password(new_password)
        user.save()

        messages.success(request, "Password changed successfully!")
        return redirect("settings")

    return render(request, "settings.html")

def student_main(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    try:
        studentinfo = Member.objects.get(id=user_id)
    except Member.DoesNotExist:
        return redirect('/login')

    return render(request, 'student-main.html', {'studentinfo': studentinfo})


def admin_main(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/mentor_login')

    try:
        admininfo = AdminLogin.objects.get(id=user_id)
    except AdminLogin.DoesNotExist:
        return redirect('/mentor_login')

    return render(request, 'admin_main.html', {'admininfo': admininfo})


def edit_student(request):
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        student = get_object_or_404(Member, id=student_id)

        new_name = request.POST.get("name")
        new_email = request.POST.get("email")
        new_username = request.POST.get("username")
        new_phone = request.POST.get("phone")
        new_id_number = request.POST.get("id_number")
        new_dob = request.POST.get("date_of_birth")
        new_gender = request.POST.get("gender")

        if Member.objects.filter(email=new_email).exclude(id=student.id).exists():
            return JsonResponse({"error": "Email is already taken by another student."})

        if Member.objects.filter(username=new_username).exclude(id=student.id).exists():
            return JsonResponse({"error": "Username is already taken by another student."})

        if Member.objects.filter(phone=new_phone).exclude(id=student.id).exists():
            return JsonResponse({"error": "Phone number is already taken by another student."})

        if Member.objects.filter(id_number=new_id_number).exclude(id=student.id).exists():
            return JsonResponse({"error": "ID number is already taken by another student."})

        student.name = new_name
        student.email = new_email
        student.username = new_username
        student.phone = new_phone
        student.id_number = new_id_number
        student.date_of_birth = new_dob
        student.gender = new_gender
        student.save()

        return JsonResponse({"success": "Student information updated successfully!"})

    return JsonResponse({"error": "Invalid request."})

def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})

def mentor_courses(request, user_id):
    admininfo = get_object_or_404(AdminLogin, id=user_id)
    courses = Course.objects.filter(mentor=admininfo)

    if request.method == "POST" and "add_course" in request.POST:
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.mentor = admininfo
            course.save()
            messages.success(request, "Course added successfully!")
        else:
            messages.error(request, "Please correct the errors below.")
        return redirect("mentor_courses", user_id=admininfo.id)

    form = CourseForm()
    return render(request, "upload_courses.html", {
        "courses": courses,
        "admininfo": admininfo,
        "user": admininfo,  # for admin_main.html
        "form": form,
    })

# Add a new course
def add_course(request, user_id):
    admininfo = get_object_or_404(AdminLogin, id=user_id)

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.mentor = admininfo  # Assign logged-in mentor
            course.save()
            messages.success(request, "✅ Course added successfully!")
            return redirect("mentor_courses", user_id=admininfo.id)
    else:
        form = CourseForm()

    return render(request, "add_courses.html", {
        "form": form,
        "admininfo": admininfo
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponseRedirect

@transaction.atomic
def add_module(request):
    if request.method != "POST":
        return redirect("mentor_courses", user_id=request.user.id)

    course_id = request.POST.get("course_id")
    module_title = (request.POST.get("module_title") or "").strip()
    order_str = request.POST.get("order")
    topics = [t.strip() for t in request.POST.getlist("topics[]") if t.strip()]

    course = get_object_or_404(Course, id=course_id)

    if not module_title or not topics:
        messages.error(request, "❌ Please fill in all required fields.")
        return redirect("mentor_courses", user_id=course.mentor.id)

    try:
        module_order = int(order_str) if order_str else 1
    except ValueError:
        module_order = 1

    module, module_created = Module.objects.get_or_create(
        course=course,
        title=module_title,
        defaults={"order": module_order},
    )

    if not module_created and module_order and module.order != module_order:
        module.order = module_order
        module.save(update_fields=["order"])

    topics_created, subtopics_created = 0, 0

    for idx, topic_title in enumerate(topics, start=1):
        sub_list = [s.strip() for s in request.POST.getlist(f"subtopics_{idx}[]") if s.strip()]

        topic_obj, topic_created = Topic.objects.get_or_create(
            module=module,
            title=topic_title,
            defaults={"order": (Topic.objects.filter(module=module).count() + 1)},
        )
        if topic_created:
            topics_created += 1

        for sub_title in sub_list:
            _, sub_created = Subtopic.objects.get_or_create(
                topic=topic_obj,
                title=sub_title,
                defaults={"order": (Subtopic.objects.filter(topic=topic_obj).count() + 1)},
            )
            if sub_created:
                subtopics_created += 1

    if module_created:
        msg = f"✅ Module '{module.title}' created. Added {topics_created} topic(s) and {subtopics_created} subtopic(s)."
    else:
        msg = f"ℹ️ Module '{module.title}' already existed. Added {topics_created} topic(s) and {subtopics_created} subtopic(s)."

    messages.success(request, msg)
    
    # Redirect back to the same page with the course selected
    redirect_url = reverse("mentor_courses", kwargs={"user_id": course.mentor.id})
    return HttpResponseRedirect(f"{redirect_url}?course={course_id}")


def get_course_modules(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = course.modules.prefetch_related('topics__subtopics')
    context = {'course': course, 'modules': modules, 'admininfo': course.mentor}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'partials/modules_section.html', context)
    return render(request, 'upload_courses.html', context)



def course_modules_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Fetch all modules with topics and subtopics preloaded to avoid multiple queries
    modules = course.modules.prefetch_related('topics__subtopics')
    return render(request, 'course_modules.html', {
        'course': course,
        'modules': modules
    })

def add_lesson(request, module_id):
    module = get_object_or_404(Module, id=module_id)

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module

            # Handle video type
            video_type = form.cleaned_data.get("video_type")
            if video_type == "youtube":
                lesson.youtube_url = form.cleaned_data.get("youtube_url")
                lesson.video = None
            elif video_type == "upload":
                lesson.video = request.FILES.get("video")
                lesson.youtube_url = None
            else:
                lesson.video = None
                lesson.youtube_url = None

            # Handle notes
            if request.FILES.get("notes"):
                lesson.notes = request.FILES["notes"]

            # Handle recording
            if request.FILES.get("recording"):
                lesson.recording = request.FILES["recording"]

            # Multiple links
            links = request.POST.getlist("links[]")
            lesson.links = links if links else None

            lesson.save()
            messages.success(request, "✅ Lesson added successfully!")

            return redirect("mentor_courses", user_id=module.course.mentor.id)  # ✅ success → go back
        else:
            # ❌ failure → stay on same page, re-render with errors
            lessons = Lesson.objects.filter(module=module).order_by("order")
            admininfo = module.course.mentor
            return render(
                request,
                "upload_courses.html",
                {
                    "form": form,
                    "module": module,
                    "lessons": lessons,
                    "admininfo": admininfo,
                    "open_modal": True,  # ✅ tell template to reopen modal
                }
            )

    # GET request
    return redirect("mentor_courses", user_id=module.course.mentor.id)


def get_module_lessons(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    lessons = module.lessons.all()  # ordered by Meta.order
    context = {
        "module": module,
        "lessons": lessons,
        "course": module.course,
        "admininfo": module.course.mentor,
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "partials/lessons_section.html", context)

    return render(request, "upload_courses.html", context)



import requests
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from cloudinary.utils import cloudinary_url
from .models import Lesson

def download_note(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not lesson.notes:
        return HttpResponse("No notes available.", status=404)
    
    try:
        # Get the public_id - ensure it includes the file extension
        public_id = lesson.notes.public_id
        
        # If public_id doesn't have an extension, try to determine it
        if '.' not in public_id:
            # You might need to store the original filename separately
            public_id += '.pdf'  # Assuming PDF as default
        
        # Build signed URL
        file_url, options = cloudinary_url(
            public_id,
            resource_type="raw",
            type="authenticated",
            sign_url=True,
            secure=True
        )
        
        # For debugging - print the URL to console or log
        print(f"Cloudinary URL: {file_url}")
        
        # Option 1: Redirect directly to Cloudinary (most efficient)
        return HttpResponseRedirect(file_url)
        
        # Option 2: Proxy the content through your server (if you need access control)
        """
        response = requests.get(file_url, stream=True)
        if response.status_code != 200:
            return HttpResponse(
                "Notes are temporarily unavailable. Please try again later.",
                status=404
            )
        
        # Serve the file
        filename = public_id.split("/")[-1]
        django_response = HttpResponse(
            response.content,
            content_type=response.headers.get("Content-Type", "application/pdf")
        )
        django_response["Content-Disposition"] = f'inline; filename="{filename}"'
        return django_response
        """
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error generating download URL: {str(e)}")
        return HttpResponse(
            "An error occurred while preparing the download. Please contact support.",
            status=500
        )

# student_profile
def student_profile(request, studentinfo):
    infos = get_object_or_404(Member, id=studentinfo)

    if request.method == 'POST':
        form = StudentEditForm(request.POST, request.FILES, instance=infos)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_profile', studentinfo=studentinfo)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentEditForm(instance=infos)

    return render(request, 'profiles/student_profile.html', {
        'form': form,
        'infos': infos,
        'studentinfo': infos, 
        
    })

# student change password
def change_password_s(request, id):
    infos = get_object_or_404(Member, id=id)

    if request.method == "POST":
        current_password = request.POST.get("currentPassword")
        new_password = request.POST.get("newPassword")
        confirm_password = request.POST.get("confirmNewPassword")

        if not check_password(current_password, infos.password):
            messages.error(request, "Current password is incorrect.")
            return redirect("student_profile", studentinfo=id)

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("student_profile", studentinfo=id)

        infos.password = make_password(new_password)
        infos.save()

        messages.success(request, "Password updated successfully!")
        return redirect("student_profile", studentinfo=id)

    return redirect("student_profile", studentinfo=id)


@csrf_protect
def delete_account_s(request, id):
    infos = get_object_or_404(Member, id=id)

    if request.method == "POST":
        email_input = request.POST.get("email")

        if not email_input:
            messages.error(request, "Please enter your email.")
            return redirect("student_profile", id=id)

        if email_input.strip().lower() != infos.email.lower():
            messages.error(request, "Email does not match. Account not deleted.")
            return redirect("student_profile", id=id)

        logout(request)

        infos.delete()

        messages.success(request, "Your account has been deleted successfully.")
        return redirect("register")  # Ensure 'register' is a valid URL name

    return redirect("student_profile", id=id)

# mentor profile

def mentor_profile(request, admininfo):
    infos = get_object_or_404(AdminLogin, id=admininfo)

    if request.method == 'POST':
        form = MentorEditForm(request.POST, request.FILES, instance=infos)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('mentor_profile', admininfo=admininfo)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MentorEditForm(instance=infos)

    return render(request, 'profiles/mentor_profile.html', {
        'form': form,
        'infos': infos,
        'admininfo': infos  
    })

def change_password_m(request, id):
    infos = get_object_or_404(AdminLogin, id=id)

    if request.method == "POST":
        current_password = request.POST.get("currentPassword")
        new_password = request.POST.get("newPassword")
        confirm_password = request.POST.get("confirmNewPassword")

        # 1. Check current password
        if not infos.check_password(current_password):
            messages.error(request, "❌ Current password is incorrect.")
            return redirect("mentor_profile", admininfo=id)

        # 2. Confirm new password match
        if new_password != confirm_password:
            messages.error(request, "⚠️ New passwords do not match.")
            return redirect("mentor_profile", admininfo=id)

        # 3. Prevent reusing the same password
        if infos.check_password(new_password):
            messages.warning(request, "⚠️ New password cannot be the same as current password.")
            return redirect("mentor_profile", admininfo=id)

        # 4. Save new hashed password
        infos.set_password(new_password)

        messages.success(request, "✅ Password updated successfully!")
        return redirect("mentor_profile", admininfo=id)

    messages.error(request, "Invalid request method.")
    return redirect("mentor_profile", admininfo=id)


@csrf_protect
def delete_account_m(request, id):
    infos = get_object_or_404(AdminLogin, id=id)

    if request.method == "POST":
        email_input = request.POST.get("email")

        if not email_input:
            messages.error(request, "Please enter your email.")
            return redirect("mentor_profile", id=id)

        if email_input.strip().lower() != infos.email.lower():
            messages.error(request, "Email does not match. Account not deleted.")
            return redirect("mentor_profile", id=id)

        logout(request)

        infos.delete()

        messages.success(request, "Your account has been deleted successfully.")
        return redirect("index")  # Ensure 'register' is a valid URL name

    return redirect("mentor_profile", id=id)

#registered students view

def registered_students(request):
    username = request.session.get('username')
    if not username:
        return redirect('admin_login')
    
    try:
        admininfo = AdminLogin.objects.get(username=username)
    except AdminLogin.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_login')

    # Get all students and order them
    student_list = Member.objects.all().order_by('name')
    
    # Set up pagination - 10 students per page
    paginator = Paginator(student_list, 10)
    page = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'student_record/student.html', {
        'admininfo': admininfo,
        'page_obj': page_obj,  # Paginated students
    })


#contact messages
def contact_message(request):
    username = request.session.get('username')
    if not username:
        return redirect('admin_login')

    try:
        admininfo = AdminLogin.objects.get(username=username)
    except AdminLogin.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_login')
    
    # Get search query
    search_query = request.GET.get('q', '')
    
    # Get sort option
    sort_option = request.GET.get('sort', 'newest')
    
    # Base queryset
    contact_list = Contact.objects.all()
    
    # Apply search filter if provided
    if search_query:
        contact_list = contact_list.filter(
            Q(name__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(message__icontains=search_query)
        )
    
    # Apply sorting
    if sort_option == 'oldest':
        contact_list = contact_list.order_by('id')
    else:  # newest first by default
        contact_list = contact_list.order_by('-id')
    
    # Pagination
    paginator = Paginator(contact_list, 10)  # Show 10 contacts per page
    page_number = request.GET.get('page')
    contacts = paginator.get_page(page_number)
    
    return render(request, 'contact_messages.html', {
        'admininfo': admininfo,
        'contacts': contacts,
        'search_query': search_query,
        'sort_option': sort_option,
        
    })

#notifications
def latest_messages(request):
    messages_count = Contact.objects.count()  # or filter for unread if you track it
    latest_messages = Contact.objects.order_by('-created_at')[:5]
    return {
        'messages_count': messages_count,
        'latest_messages': latest_messages,
    }


