from django.contrib import admin
from TechApp.models import Member, AdminLogin, Contact,Course,Enrollment,Lesson,Module,Topic,Subtopic,Message,Conversation,LessonProgress

# Register your models here.

admin.site.register(Member)
admin.site.register(AdminLogin)
admin.site.register(Contact)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(Topic)
admin.site.register(Subtopic)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(LessonProgress)


