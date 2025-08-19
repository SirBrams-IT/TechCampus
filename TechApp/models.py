from datetime import date
import random
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from cloudinary.models import CloudinaryField  # ✅ Cloudinary import


def generate_otp():
    return str(random.randint(100000, 999999))


class Member(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    id_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    profile_image = CloudinaryField('image', folder="profile_images", null=True, blank=True)  # ✅ Cloudinary
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    # OTP Fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    class User(models.Model):
        email = models.CharField(max_length=100)
        username = models.CharField(max_length=50)
        password = models.CharField(max_length=50)
        is_superuser = models.BooleanField(default=False)

        def __str__(self):
            return self.email

    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=3)
        self.save()

    def verify_otp(self, otp):
        if self.is_otp_valid(otp):
            self.is_active = True
            self.clear_otp()
            self.save()
            return True
        return False

    def is_otp_valid(self, otp):
        return self.otp_code == otp and self.otp_expires_at > timezone.now()

    def clear_otp(self):
        self.otp_code = None
        self.otp_expires_at = None
        self.save()

    def __str__(self):
        return self.email


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=13)
    message = models.CharField(max_length=100)

    def __str__(self):
        return self.name


def validate_age(value):
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 30 or age > 75:
        raise ValidationError(f'Age must be between 30 and 75 years. Current age: {age} years.')


class AdminLogin(models.Model):
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, unique=True)
    id_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(validators=[validate_age])
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    profile_image = CloudinaryField('image', folder="admin_profiles", blank=True, null=True)  # ✅ Cloudinary
    password = models.CharField(max_length=100)

    # OTP Fields for password reset
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=3)
        self.save()

    def verify_otp(self, otp):
        if self.is_otp_valid(otp):
            self.clear_otp()
            self.save()
            return True
        return False

    def is_otp_valid(self, otp):
        return self.otp_code == otp and self.otp_expires_at > timezone.now()

    def clear_otp(self):
        self.otp_code = None
        self.otp_expires_at = None
        self.save()

    def __str__(self):
        return self.name

class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = CloudinaryField('file', folder="assignments")  # ✅ Cloudinary
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_assignments')

    def __str__(self):
        return self.title


class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    submitted_file = CloudinaryField('file', folder="submissions", null=True, blank=True)  # ✅ Cloudinary
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('Not Submitted', 'Not Submitted'),
        ('Submitted', 'Submitted'),
        ('Due', 'Due'),
        ('Late', 'Late')
    ], default='Not Submitted')
    marked = models.BooleanField(default=False)
    grade = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.submitted_at and self.submitted_at > self.assignment.due_date:
            self.status = 'Late'
        elif self.submitted_at:
            self.status = 'Submitted'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Submission by {self.student.username} for {self.assignment.title}"


class CourseStatus(models.Model):
    STATUS_CHOICES = [
        ('Enrolled', 'Enrolled'),
        ('Submitted', 'Submitted'),
        ('Due', 'Due'),
        ('Marked', 'Marked'),
    ]
    user = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='course_statuses')
    course_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Enrolled')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.course_name}: {self.status}"


COURSE_CHOICES = [
    ('Web Development', 'WD111'),
    ('Android Development', 'AD111'),
    ('IT Support', 'IT111'),
    ('Graphic Design', 'GD111'),
    ('Cybersecurity', 'CS111'),
    ('Advanced Excel', 'AE111'),
    ('CCTV Installation', 'CCTV111'),
    ('Project Management System', 'PMS111'),
    ('AI', 'AI111'),
    ('Cloud Computing', 'CC111'),
]

class Course(models.Model):
    mentor = models.ForeignKey(AdminLogin, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return self.title
    
class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    video = CloudinaryField(resource_type="video", blank=True, null=True)
    resource = CloudinaryField(resource_type="raw", blank=True, null=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.module.title} - {self.title}"

class Enrollment(models.Model):
    student = models.ForeignKey('Member', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    learning_status = models.CharField(max_length=20, choices=[
        ('Not Started', 'Not Started'),
        ('Started', 'Started')
    ], default='Not Started')

    def __str__(self):
        return f"{self.student} - {self.course.title} ({self.learning_status})"
