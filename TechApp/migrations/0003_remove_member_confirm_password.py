# Generated by Django 5.1.6 on 2025-02-15 11:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('TechApp', '0002_adminlogin_otp_code_adminlogin_otp_expires_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='confirm_password',
        ),
    ]
