# TechApp/models.py
from datetime import date
import random
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db import models
from django.db import IntegrityError
from cloudinary.models import CloudinaryField


def generate_otp():
    return str(random.randint(100000, 999999))


def validate_age(value):
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 30 or age > 75:
        raise ValidationError(f'Age must be between 30 and 75 years. Current age: {age} years.')


# ---------- Custom Unified User ----------
class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('mentor', 'Mentor'),
        ('admin', 'Admin'),
    )

    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    id_number = models.CharField(max_length=20, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        null=True,
        blank=True
    )
    profile_image = CloudinaryField('image', folder='profile_images', null=True, blank=True)

    # role & IDs
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    student_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    mentor_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_prompt_shown = models.BooleanField(default=False) #profile %completion


    # OTP fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    # soft delete, timestamps
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # use email as login identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # username still required for display

    def __str__(self):
        return f"{self.username} ({self.role})"

    #-------------profile % completion helper-----------
    def profile_completion(self):
        """Return profile completion percentage based on filled fields."""
        fields = [
            self.name,
            self.username,
            self.email,
            self.phone,
            self.id_number,
            self.date_of_birth,
            self.gender,
            self.profile_image
        ]
        filled = len([f for f in fields if f])
        return int((filled / len(fields)) * 100)    

    # ---------- OTP helpers ----------
    def generate_otp(self):
        self.otp_code = generate_otp()
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=3)
        self.save(update_fields=["otp_code", "otp_expires_at"])

    def is_otp_valid(self, otp):
        return (
            self.otp_code == str(otp)
            and self.otp_expires_at
            and self.otp_expires_at > timezone.now()
        )

    def verify_otp(self, otp):
        if self.is_otp_valid(otp):
            self.is_active = True
            self.clear_otp()
            self.save(update_fields=["is_active"])
            return True
        return False

    def clear_otp(self):
        self.otp_code = None
        self.otp_expires_at = None
        self.save(update_fields=["otp_code", "otp_expires_at"])

    # ---------- Auto-generate Student No / Mentor ID safely ----------
    def save(self, *args, **kwargs):
        current_year = timezone.now().year

        # Hash password if not already hashed
        if self.password and not self.password.startswith('pbkdf2_'):
            self.set_password(self.password)

        # Generate unique student number
        if self.role == "student" and not self.student_number:
            attempt = 0
            while True:
                last_user = User.objects.filter(
                    role="student", student_number__endswith=f"/{current_year}"
                ).order_by('-id').first()

                if last_user and last_user.student_number:
                    try:
                        last_num = int(last_user.student_number.split('/')[1])
                    except:
                        last_num = 0
                    new_num = last_num + 1
                else:
                    new_num = 1

                self.student_number = f"STVC/{new_num:04d}/{current_year}"

                try:
                    super(User, self).save(*args, **kwargs)
                    break
                except IntegrityError:
                    attempt += 1
                    if attempt > 10:
                        raise ValueError("Unable to generate unique student number. Please try again.")

            return  # already saved

        # Generate unique mentor ID
        if self.role == "mentor" and not self.mentor_id:
            attempt = 0
            while True:
                last_user = User.objects.filter(role="mentor").order_by('-id').first()
                if last_user and last_user.mentor_id:
                    try:
                        last_num = int(last_user.mentor_id.split('/')[1])
                    except:
                        last_num = 0
                    new_num = last_num + 1
                else:
                    new_num = 1

                self.mentor_id = f"MENT/{new_num:03d}/{current_year}"

                try:
                    super(User, self).save(*args, **kwargs)
                    break
                except IntegrityError:
                    attempt += 1
                    if attempt > 10:
                        raise ValueError("Unable to generate unique mentor ID. Please try again.")

            return  # already saved

        # Default save if IDs already exist
        super().save(*args, **kwargs)

    # ---------- Messaging helper shims ----------
    def get_conversations(self):
        return getattr(self, "conversations", None) and self.conversations.all()

    def get_unread_count(self):
        from django.db.models import Q
        from .models import Message  # local import to avoid circular import risk
        return (
            Message.objects.filter(conversation__in=self.conversations.all())
            .exclude(sender=self)
            .filter(read=False)
            .count()
        )


# ---------- Conversation & Messages (use unified User) ----------
class Conversation(models.Model):
    CONVERSATION_TYPES = (
        ('dm', 'Direct Message'),
        ('forum', 'Forum'),
    )

    name = models.CharField(max_length=255, blank=True, null=True)
    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPES)  
    # normal participants
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    # admins of the conversation
    admin_participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='admin_conversations',blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.conversation_type == 'dm' and self.participants.count() != 2:
            raise ValidationError("Direct messages must have exactly 2 participants")

    def __str__(self):
        if self.conversation_type == 'dm':
            participants = list(self.participants.all())
            return f"DM: {', '.join([p.name or p.username for p in participants])}"
        return f"Forum: {self.name}"

#------------Message model------
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def clean(self):
        if not self.sender:
            raise ValidationError("Message must have a sender")

    def get_sender_name(self):
        return self.sender.name or self.sender.username

    def get_sender_type(self):
        return getattr(self.sender, "role", None) or "user"

    def __str__(self):
        sender_name = self.get_sender_name()
        return f"{sender_name}: {self.content[:50]}"

# ---------- Courses, Modules, Topics, Lessons ----------
class Course(models.Model):
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role__in': ['mentor', 'admin']})
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Course fee in KES")
    duration = models.CharField(max_length=50, help_text="e.g. '3 months', '10 weeks'")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    course_images = CloudinaryField('image', folder='course_images', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "".join([word[0].upper() for word in self.title.split()[:2]])
            number = 200 + Course.objects.count()
            self.code = f"{prefix}-{number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.code}) - KES {self.amount}"


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
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in url:
            video_id = url.split("shorts/")[-1].split("?")[0]
        else:
            return url
        return f"https://www.youtube.com/embed/{video_id}"

    def __str__(self):
        return f"{self.module} - {self.title}"


# ---------- Progress & Enrollment ----------
class LessonProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress", limit_choices_to={'role': 'student'})
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_progress")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "lesson")

    def __str__(self):
        return f"{self.student} - {self.lesson} - {'Completed' if self.completed else 'Pending'}"


STATUS_CHOICES = [
    ('initiated', 'Initiated (STK started)'),
    ('paid_pending_approval', 'Paid (Pending Mentor Approval)'),
    ('approved', 'Approved (Accessible to Student)'),
    ('failed', 'Payment Failed'),
    ('rejected', 'Rejected by Mentor'),
]


class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments', limit_choices_to={'role': 'student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')

    # Snapshots for easy display + history
    mentor_name = models.CharField(max_length=255)
    student_name = models.CharField(max_length=255)
    course_title = models.CharField(max_length=255)
    course_code = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    duration = models.CharField(max_length=50, blank=True, null=True)

    # MPESA info
    merchant_request_id = models.CharField(max_length=255, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=255, blank=True, null=True)
    transaction_code = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='initiated')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student_name} -> {self.course_title} ({self.status})"


# ---------- Contact ----------
class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=13)
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
