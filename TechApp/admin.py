from django.contrib import admin
from TechApp.models import Member, AdminLogin, Contact,Submission,Assignment,CourseStatus,Course,Enrollment,Lesson,Module

# Register your models here.

admin.site.register(Member)
admin.site.register(AdminLogin)
admin.site.register(Contact)
admin.site.register(Submission)
admin.site.register(Assignment)
admin.site.register(CourseStatus)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Module)
admin.site.register(Lesson)


