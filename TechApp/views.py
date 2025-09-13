import json
from django.http import FileResponse
from django.db import transaction
from datetime import timezone
import requests
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
from TechApp.forms import  EnrollmentForm, StudentForm,StudentEditForm, MentorEditForm, AssignmentForm,SubmissionForm,AdminForm, CourseForm, ModuleForm, LessonForm
from TechApp.models import Course, Member, Contact, AdminLogin, Assignment, Submission ,Module, Lesson,Topic, Subtopic
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import random
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.contrib.auth.decorators import login_required



def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))

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

def student_dashboard(request):
    username = request.session.get('username')

    if not username:
        return redirect('login')

    try:
        studentinfo = Member.objects.get(username=username)
    except Member.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    return render(request, 'student_dashboard.html', {'studentinfo': studentinfo})

def logout_student(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('login')

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if AdminLogin.objects.filter(username=username, password=password).exists():
            admininfo = AdminLogin.objects.filter(username=username).first()

            request.session['username'] = username
            request.session['admin_id'] = admininfo.id

            messages.success(request, "Login successful! Welcome to the admin dashboard.")  # Set success message
            return redirect('admin_dashboard')  # Redirect with message

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_superuser:
                auth_login(request, user)

                messages.success(request, "Login successful! Redirecting to admin panel.")  # Set success message
                return redirect('/admin/')  # Redirect with message

        messages.error(request, "Invalid username or password")  # Error message for incorrect login

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

    contacts = Contact.objects.all()

    return render(request, 'admin_dashboard.html', {
        'admininfo': admininfo,
        'contacts': contacts,
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

def available_courses(request,user_id):
    studentinfo = get_object_or_404(Member, id=user_id)
    return render(request,'available_courses.html',{'studentinfo':studentinfo})

def payment(request,user_id):
    studentinfo = get_object_or_404(Member, id=user_id)
    return render(request, 'payment.html',{'studentinfo':studentinfo})

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




def token(request):
    consumer_key = 'RPxUwLYGGMVJRkWofm0K09qnWfH60pwxg2kSVFmFERrQEow5'
    consumer_secret = '8qGJf8mLmhGAore5FC06nncbbx3WNV4apitG7hMzLrmTMrrzNrtH092LDGSlVt5C'
    api_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    r = requests.get(api_URL, auth=HTTPBasicAuth(
        consumer_key, consumer_secret))
    mpesa_access_token = json.loads(r.text)
    validated_mpesa_access_token = mpesa_access_token["access_token"]

    return render(request, 'token.html', {"token":validated_mpesa_access_token})

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


def stk(request):
    if request.method == "POST":
        phone = request.POST['phone']
        amount = request.POST['amount']
        access_token = MpesaAccessToken.validated_mpesa_access_token
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        payment_request = {
            "BusinessShortCode": LipanaMpesaPpassword.Business_short_code,
            "Password": LipanaMpesaPpassword.decode_password,
            "Timestamp": LipanaMpesaPpassword.lipa_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": LipanaMpesaPpassword.Business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
            "AccountReference": "SirBrams Tech Virtual Campus",
            "TransactionDesc": "Virtual Campus Charges"
        }
        response = requests.post(api_url, json=payment_request, headers=headers)

        # Check the response status for success or failure
        if response.status_code == 200:
            # Redirect to payment page with a success message
            return redirect('/courses?status=success')
        else:
            # Redirect to payment page with a failure message
            return redirect('/payment?status=failure')

    return render(request, 'payment.html')


def records(request, user_id):
    allmembers = Member.objects.all()
    admininfo = get_object_or_404(AdminLogin, id=user_id)
    return render(request,'records.html',{'member':allmembers,'admininfo':admininfo})

def add_cours(request):
    if request.method == "POST":
        form = AssignmentForm(request.POST, request.FILES, user=request.user)  # Pass user to form
        if form.is_valid():
            assignment = form.save(commit=False)  # Don't save yet
            assignment.mentor = AdminLogin.objects.get(username=request.user.username)  # Assign correct mentor
            assignment.save()  # Now save
            return redirect('/mentor_viewstatus')

    else:
        form = AssignmentForm(user=request.user)  # Pass user here

    return render(request, 'add_cours.html', {'form': form})


def mentor_viewstatus(request):
    if not request.user.is_authenticated:
        return redirect('/mentor_login/')  # Redirects to login page

    assignments = Assignment.objects.filter(mentor=request.user)
    submissions = Submission.objects.filter(assignment__in=assignments)

    if request.method == 'POST':
        submission_id = request.POST.get('submission_id')
        submission = get_object_or_404(Submission, id=submission_id)
        form = SubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            submission.marked = True
            form.save()
            return redirect('mentor_viewstatus')

    else:
        form = SubmissionForm()

    return render(request, 'mentor_viewstatus.html', {
        'submissions': submissions,
        'form': form
    })


def student_assignments(request):
    # Fetch all assignments
    studentinfo = Member.objects.filter(username=request.POST.get('username')).first()
    assignments = Assignment.objects.all()
    submissions = Submission.objects.filter(student=request.user)

    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        action = request.POST.get('action')

        # Fetch assignment
        assignment = get_object_or_404(Assignment, id=assignment_id)

        # Check if submission exists for this assignment
        submission = submissions.filter(assignment=assignment).first()

        if action == 'submit':
            form = SubmissionForm(request.POST, request.FILES, instance=submission)
            if form.is_valid():
                submission = form.save(commit=False)
                submission.student = request.user
                submission.assignment = assignment
                submission.submitted_at = timezone.now()
                submission.save()
                return redirect('student_assignments')
        elif action == 'redo' and submission:
            submission.marked = False  # Unmark for re-evaluation
            submission.save()
            return redirect('student_assignments')
        elif action == 'delete' and submission:
            submission.delete()
            return redirect('student_assignments')

    return render(request, 'student_assignments.html', {
        'studentinfo': studentinfo,
        'assignments': assignments,
        'submissions': submissions,
        'submission_form': SubmissionForm(),
    })


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
    return redirect('admin_dashboard')


def contacts(request):
   if request.method=='POST':
       mycontact = Contact(
           name = request.POST['name'],
           email = request.POST['email'],
           phone = request.POST['phone'],
           message = request.POST['message']
       )
       mycontact.save()
       return redirect('/index')

   else:
       return render(request,'contact.html')

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

def enroll_course(request):
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_dashboard')
    else:
        form = EnrollmentForm()
    return render(request, 'enroll_course.html', {'form': form})

def course_list(request):
    courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses})

def mentor_courses(request, user_id):
    admininfo = get_object_or_404(AdminLogin, id=user_id)
    courses = Course.objects.filter(mentor=admininfo)

    if request.method == "POST" and "add_course" in request.POST:
        title = request.POST.get("title")
        description = request.POST.get("description")

        if title and description:
            Course.objects.create(
                title=title,
                description=description,
                mentor=admininfo,
            )
            messages.success(request, "Course added successfully!")
        else:
            messages.error(request, "Please fill in all required fields.")

        return redirect("mentor_courses", user_id=admininfo.id)

    return render(request, "upload_courses.html", {
        "courses": courses,
        "admininfo": admininfo,
        "user": admininfo,  # 👈 Added so admin_main.html works
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

def learning(request, studentinfo):
    student = Member.objects.filter(id=studentinfo).first()
    return render(request, "learning_page.html", {"studentinfo": student})

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
        'studentinfo': infos   # 👈 add this line
    })


def change_password_s(request, id):
    infos = get_object_or_404(Member, id=id)

    if request.method == "POST":
        current_password = request.POST.get("currentPassword")
        new_password = request.POST.get("newPassword")
        confirm_password = request.POST.get("confirmNewPassword")

        if not check_password(current_password, infos.password):
            messages.error(request, "Current password is incorrect.")
            return redirect("student_profile", id=id)

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("student_profile", id=id)

        infos.password = make_password(new_password)
        infos.save()

        messages.success(request, "Password updated successfully!")
        return redirect("student_profile", id=id)

    return redirect("student_profile", id=id)


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

        if not check_password(current_password, infos.password):
            messages.error(request, "Current password is incorrect.")
            return redirect("mentor_profile", id=id)

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("mentor_profile", id=id)

        infos.password = make_password(new_password)
        infos.save()

        messages.success(request, "Password updated successfully!")
        return redirect("mentor_profile", id=id)

    return redirect("mentor_profile", id=id)


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
        return redirect("register")  # Ensure 'register' is a valid URL name

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