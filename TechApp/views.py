import json
from datetime import timezone
import requests
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.core.mail import send_mail
from django.http import HttpResponse
from requests.auth import HTTPBasicAuth
from urllib3 import request

from TechApp.credentials import MpesaAccessToken, LipanaMpesaPpassword
from django.shortcuts import  redirect,render, get_object_or_404
from django.contrib.auth import logout
from django.contrib import messages
from TechApp.forms import FileUploadForm, StudentForm, AssignmentForm,SubmissionForm,AdminForm
from TechApp.models import Member, Contact, FileModel, AdminLogin,Assignment,Submission
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
import random
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.utils import timezone


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
            return redirect('/register')
        if Member.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('/register')
        if Member.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number is already taken.")
            return redirect('/register')
        if Member.objects.filter(id_number=id_number).exists():
            messages.error(request, "ID number is already taken.")
            return redirect('/register')

        # Validate password match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('/register')

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
            return redirect('/student_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('/login')

    return render(request, 'login.html')


def student_dashboard(request):
    username = request.session.get('username')

    if not username:
        return redirect('/login')

    try:
        studentinfo = Member.objects.get(username=username)
    except Member.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('/login')

    return render(request, 'student_dashboard.html', {'studentinfo': studentinfo})

def logout_student(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('/login')

def admin_login(request):
    if request.method == "POST":

        if AdminLogin.objects.filter(username=request.POST.get('username'), password=request.POST.get('password')).exists():

            admininfo = AdminLogin.objects.filter(username=request.POST.get('username')).first()
            return render(request, 'admin_dashboard.html', {'admininfo': admininfo})
        else:

            return render(request, 'mentor_login.html', {'error': 'Invalid username or password'})

    return render(request, 'mentor_login.html')

def admin_dashboard(request):
    username = request.session.get('username')

    if not username:
        return redirect('admin_login')  # Redirect to login if session is missing

    try:
        admininfo = AdminLogin.objects.get(username=username)
    except AdminLogin.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_login')

    return render(request, 'admin_dashboard.html', {'admininfo': admininfo})

def logout_mentor(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('/admin_login')

def courses(request):
        return render(request, 'login.html')

def available_courses(request):
    return render(request,'available_courses.html')

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

    return render(request, "resend_reset_otp.html")


def payment(request):
    return render(request, 'payment.html')

def token(request):
    consumer_key = 'RPxUwLYGGMVJRkWofm0K09qnWfH60pwxg2kSVFmFERrQEow5'
    consumer_secret = '8qGJf8mLmhGAore5FC06nncbbx3WNV4apitG7hMzLrmTMrrzNrtH092LDGSlVt5C'
    api_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    r = requests.get(api_URL, auth=HTTPBasicAuth(
        consumer_key, consumer_secret))
    mpesa_access_token = json.loads(r.text)
    validated_mpesa_access_token = mpesa_access_token["access_token"]

    return render(request, 'token.html', {"token":validated_mpesa_access_token})

def add_student(request):
    if request.method == 'POST':
        # Extracting form data
        name = request.POST['name']
        email = request.POST['email']
        username = request.POST['username']
        phone = request.POST['phone']
        id_number = request.POST['id_number']
        date_of_birth = request.POST['date']
        gender = request.POST['gender']

        # Validation for unique fields
        if Member.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken.")
            return redirect('/add_student')
        elif Member.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('/add_student')
        elif Member.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number is already taken.")
            return redirect('/add_student')
        elif Member.objects.filter(id_number=id_number).exists():
            messages.error(request, "ID number is already taken.")
            return redirect('/add_student')

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
            password=hashed_password,  # Save hashed password
        )
        student.save()

        messages.success(request, "Student added successfully with default password: student1234")
        return redirect('/records')

    return render(request, 'add_student.html')



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
            return redirect('/available_courses?status=success')
        else:
            # Redirect to payment page with a failure message
            return redirect('/payment?status=failure')

    return render(request, 'payment.html')


def records(request):
    allmembers = Member.objects.all()
    contacts=Contact.objects.all()

    return render(request,'records.html',{'member':allmembers,'contacts':contacts})


def add_courses(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "File uploaded successfully!")
            return redirect('/uploaded_course')
    else:
        form = FileUploadForm()
    return render(request, 'add_courses.html', {'form': form})


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
            return redirect('records')  # Use named URL instead of raw path
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentForm(instance=updatestudent)

    return render(request, 'update.html', {'form': form, 'member_u': updatestudent})

def delete_member(request, id):
    member= Member.objects.get(id = id)
    member.delete()
    return redirect('/records')

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
    return redirect('/records')

def delete_course(request,id):
    allcourses=FileModel.objects.get(id=id)
    allcourses.delete()
    return redirect('/uploaded_course')

def contacts(request):
   if request.method=='POST':
       mycontact = Contact(
           name = request.POST['name'],
           email = request.POST['email'],
           phone = request.POST['phone'],
           message = request.POST['message']
       )
       mycontact.save()
       return redirect('/contact')

   else:
       return render(request,'contact.html')


def edit_profile(request, id):
    profile = get_object_or_404(Member, id=id)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_dashboard')
        else:
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form, 'profile': profile})

def my_course(request):
    coursez = FileModel.objects.all()
    return render(request, 'mycourse.html', {'coursez':coursez})

def uploaded_course(request):
    uploads = FileModel.objects.all()
    return render(request, 'uploaded_course.html', {'uploads': uploads})

def profile_update(request, id):
    profile_update = get_object_or_404(AdminLogin, id=id)

    if request.method == 'POST':
        form = AdminForm(request.POST, request.FILES, instance=profile_update)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            request.session['username'] = profile_update.username

            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AdminForm(instance=profile_update)

    return render(request, 'profile_update.html', {'form': form, 'profile_update': profile_update})

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


def user_profile(request):
    return render(request,'user-profile.html')