from django.contrib.auth.base_user import AbstractBaseUser
from datetime import date,  timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import random
from django.utils import timezone
from django.db import models

def generate_otp():
    return str(random.randint(100000, 999999))

class Member(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=20)
    phone = models.CharField(max_length=15, unique=True)
    id_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    # OTP Fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    def generate_otp(self):
        """Generate a new OTP and set expiration time."""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=3)
        self.save()

    def verify_otp(self, otp):
        """Check if OTP is correct and not expired."""
        if self.is_otp_valid(otp):
            self.is_active = True
            self.clear_otp()
            self.save()
            return True
        return False

    def is_otp_valid(self, otp):
        """Check if OTP is valid and not expired."""
        return self.otp_code == otp and self.otp_expires_at > timezone.now()

    def clear_otp(self):
        """Clear OTP after successful verification."""
        self.otp_code = None
        self.otp_expires_at = None
        self.save()

    def __str__(self):
        return self.email

class Contact(models.Model):
   name=models.CharField(max_length=100)
   email=models.EmailField()
   phone=models.CharField(max_length=13)
   message=models.CharField(max_length=100)
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
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    password = models.CharField(max_length=100)

    # OTP Fields for password reset
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    def generate_otp(self):
        """Generate a new OTP and set expiration time for password reset."""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=3)
        self.save()

    def verify_otp(self, otp):
        """Check if OTP is correct and not expired."""
        if self.is_otp_valid(otp):
            self.clear_otp()
            self.save()
            return True
        return False

    def is_otp_valid(self, otp):
        """Check if OTP is valid and not expired."""
        return self.otp_code == otp and self.otp_expires_at > timezone.now()

    def clear_otp(self):
        """Clear OTP after successful verification."""
        self.otp_code = None
        self.otp_expires_at = None
        self.save()

    def __str__(self):
        return self.name

class FileModel(models.Model):
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    file = models.FileField(upload_to='uploads/')
    course_name = models.CharField(max_length=255)
    course_code = models.CharField(max_length=255)
    instructor = models.CharField(max_length=255)
    zoom_link = models.URLField(max_length=500, blank=True, null=True)
    google_classroom_link = models.URLField(max_length=500, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.course_name


class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to='assignments/')
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_assignments')

    def __str__(self):
        return self.title


class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    submitted_file = models.FileField(upload_to='submissions/', null=True, blank=True)
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

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_statuses')
    course_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Enrolled')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.course_name}: {self.status}"





