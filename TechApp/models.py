from datetime import date
import random
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth.hashers import make_password, check_password, identify_hasher
from decimal import Decimal


def generate_otp():
    return str(random.randint(100000, 999999))

#conversation
class Conversation(models.Model):
    CONVERSATION_TYPES = (
        ('dm', 'Direct Message'),
        ('forum', 'Forum'),
    )
    
    name = models.CharField(max_length=255, blank=True, null=True)
    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPES)
    participants = models.ManyToManyField('Member', related_name='conversations')
    admin_participants = models.ManyToManyField('AdminLogin', related_name='conversations', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        if self.conversation_type == 'dm' and self.participants.count() + self.admin_participants.count() != 2:
            raise ValidationError("Direct messages must have exactly 2 participants")
    
    def __str__(self):
        if self.conversation_type == 'dm':
            participants = list(self.participants.all()) + list(self.admin_participants.all())
            return f"DM: {', '.join([p.name for p in participants])}"
        return f"Forum: {self.name}"

#message model
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender_member = models.ForeignKey('Member', on_delete=models.CASCADE, null=True, blank=True)
    sender_admin = models.ForeignKey('AdminLogin', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def clean(self):
        if not self.sender_member and not self.sender_admin:
            raise ValidationError("Message must have a sender")
        if self.sender_member and self.sender_admin:
            raise ValidationError("Message can only have one sender")
    
    def get_sender_name(self):
        if self.sender_member:
            return self.sender_member.name
        return self.sender_admin.name
    
    def get_sender_type(self):
        if self.sender_member:
            return 'student'
        return 'mentor'
    
    def __str__(self):
        sender_name = self.get_sender_name()
        return f"{sender_name}: {self.content[:50]}"

#student model
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
     #methods for messages
    def get_conversations(self):
        return self.conversations.all()
    
    def get_unread_count(self):
        return Message.objects.filter(
            conversation__in=self.conversations.all()
        ).exclude(sender_member=self).filter(read=False).count()    

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

# Admin/Mentor Model
class AdminLogin(models.Model):
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, unique=True)
    id_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(validators=[validate_age])
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
    )
    profile_image = CloudinaryField('image', folder='admin_profiles', blank=True, null=True)
    password = models.CharField(max_length=250)

    # OTP fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    # 🔐 Password methods
    def set_password(self, raw_password):
        """Hashes and sets the password."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifies a password against the stored hash."""
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        # Ensure password is always hashed before saving
        try:
            identify_hasher(self.password)  # If it's a valid hash, fine
        except ValueError:
            self.password = make_password(self.password)  # Hash raw text
        super().save(*args, **kwargs)

    # 🔑 OTP methods
    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=3)
        self.save(update_fields=["otp_code", "otp_expires_at"])

    def verify_otp(self, otp):
        if self.is_otp_valid(otp):
            self.clear_otp()
            return True
        return False

    def is_otp_valid(self, otp):
        return self.otp_code == otp and self.otp_expires_at > timezone.now()

    def clear_otp(self):
        self.otp_code = None
        self.otp_expires_at = None
        self.save(update_fields=["otp_code", "otp_expires_at"])

    # Messaging methods
    def get_conversations(self):
        return self.conversations.all()
    
    def get_unread_count(self):
        from messaging.models import Message  # import here to avoid circular import
        return Message.objects.filter(
            conversation__in=self.conversations.all()
        ).exclude(sender_admin=self).filter(read=False).count()

    def __str__(self):
        return self.name


#course model
class Course(models.Model):
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    mentor = models.ForeignKey("AdminLogin", on_delete=models.CASCADE)
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


#module model
class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "title")

    def __str__(self):
        return self.title

#topic model
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

# lesson model
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


STATUS_CHOICES = [
    ('initiated', 'Initiated (STK started)'),
    ('paid_pending_approval', 'Paid (Pending Mentor Approval)'),
    ('approved', 'Approved (Accessible to Student)'),
    ('failed', 'Payment Failed'),
    ('rejected', 'Rejected by Mentor'),
]

class Enrollment(models.Model):
    student = models.ForeignKey(
        'TechApp.Member', on_delete=models.CASCADE, related_name='enrollments'
    )
    course = models.ForeignKey(
        'TechApp.Course', on_delete=models.CASCADE, related_name='enrollments'
    )

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
        unique_together = ('student', 'course')  # 🚨 prevents duplicate payments per course per student

    def __str__(self):
        return f"{self.student_name} -> {self.course_title} ({self.status})"

