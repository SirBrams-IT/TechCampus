from datetime import date
import random
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth.hashers import make_password, check_password


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
    profile_image = CloudinaryField('image', folder='profile_images', null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 

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
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

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
    profile_image = CloudinaryField('image', folder='admin_profiles', blank=True, null=True)
    password = models.CharField(max_length=250)

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

    def save(self, *args, **kwargs):
        # Only hash if not already hashed
        if not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)    

    def __str__(self):
        return self.name


class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = CloudinaryField('file', folder='assignments')
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_assignments')

    def __str__(self):
        return self.title


class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    submitted_file = CloudinaryField('file', folder='submissions', null=True, blank=True)
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
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    mentor = models.ForeignKey("AdminLogin", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "".join([word[0].upper() for word in self.title.split()[:2]])
            number = 200 + Course.objects.count()
            self.code = f"{prefix}-{number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.code})"


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "title")

    def __str__(self):
        return self.title


class Topic(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = ("module", "title")

    def __str__(self):
        return self.title


class Subtopic(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="subtopics")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = ("topic", "title")

    def __str__(self):
        return self.title


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    video_type = models.CharField(
        max_length=20,
        choices=[('none', 'None'), ('youtube', 'YouTube'), ('upload', 'Upload')],
        default='none'
    )
    youtube_url = models.URLField(blank=True, null=True)
    video = CloudinaryField('video', folder='lessons/videos', blank=True, null=True)
    notes = CloudinaryField('raw', folder='lessons/notes', blank=True, null=True)
    recording = CloudinaryField('video', folder='lessons/recordings', blank=True, null=True)
    links = models.JSONField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = ("module", "title")

    def youtube_embed_url(self):
        if not self.youtube_url:
            return None

        url = self.youtube_url

        # Handle standard YouTube links
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        # Handle shortened youtu.be links
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        # Handle shorts links
        elif "youtube.com/shorts/" in url:
            video_id = url.split("shorts/")[-1].split("?")[0]
        else:
            return url  # fallback if unknown format

        return f"https://www.youtube.com/embed/{video_id}"

    def __str__(self):
        return f"{self.module} - {self.title}"



class Enrollment(models.Model):
    student = models.ForeignKey('Member', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    learning_status = models.CharField(max_length=20, choices=[
        ('Not Started', 'Not Started'),
        ('Started', 'Started')
    ], default='Not Started')

    def __str__(self):
        return f"{self.student} - {self.course.title} ({self.learning_status})"
