from datetime import date

from django import forms
from TechApp.models import Course, Enrollment, Member,AdminLogin, Lesson,Module


class StudentForm(forms.ModelForm):
    class Meta:
        model = Member
        fields= '__all__'
        exclude=['password','confirm_password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Member.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Member.objects.filter(username=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if Member.objects.filter(phone=phone).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if Member.objects.filter(id_number=id_number).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This ID number is already in use.")
        return id_number

class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = '__all__'


class AdminForm(forms.ModelForm):
    profile_image = forms.ImageField(required=False)

    class Meta:
        model = AdminLogin
        exclude = ['password']

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

        # Make ID, email, and phone read-only
        self.fields['id_number'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['phone'].widget.attrs['readonly'] = True
        self.fields['username'].widget.attrs['readonly'] = True

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if age < 30 or age > 75:
            raise forms.ValidationError("Age must be between 30 and 75 years.")

        return dob    

# course form
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "amount", "duration", "course_images"]

        widgets = {
            "title": forms.Select(choices=[
                ("", "-- Select Course --"),
                ("Web Development", "Web Development"),
                ("Android Development", "Android Development"),
                ("IT Support", "IT Support"),
                ("Graphic Design", "Graphic Design"),
                ("Cybersecurity", "Cybersecurity"),
                ("Advanced Excel", "Advanced Excel"),
                ("CCTV Installation", "CCTV Installation"),
                ("Project Management System", "Project Management System"),
                ("AI", "AI"),
                ("Cloud Computing", "Cloud Computing"),
            ], attrs={"class": "form-select", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "required": True}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter fee in KES", "required": True}),
            "duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 3 months", "required": True}),
            "course_images": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["course", "title", "order"]

    def __init__(self, *args, **kwargs):
        mentor = kwargs.pop("mentor", None)
        super().__init__(*args, **kwargs)
        if mentor:
            self.fields["course"].queryset = Course.objects.filter(mentor=mentor)


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        exclude = ["module", "links"]
        fields = "__all__"

    def clean_links(self):
        links_text = self.data.getlist("links[]")
        return [link.strip() for link in links_text if link.strip()] or None
    
# Student_edit form
class StudentEditForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email', 'username', 'phone', 'id_number', 'profile_image','date_of_birth']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Member.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Member.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if Member.objects.exclude(pk=self.instance.pk).filter(phone=phone).exists():
            raise forms.ValidationError("Phone number already in use.")
        return phone

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if Member.objects.exclude(pk=self.instance.pk).filter(id_number=id_number).exists():
            raise forms.ValidationError("ID number already registered.")
        return id_number

    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if age < 18 or age > 80:
            raise forms.ValidationError("Age must be between 18 and 80 years.")

        return dob
    

# Student_edit form
class MentorEditForm(forms.ModelForm):
    class Meta:
        model = AdminLogin
        fields = ['name', 'email', 'username', 'phone', 'id_number', 'profile_image','date_of_birth']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if AdminLogin.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if AdminLogin.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if AdminLogin.objects.exclude(pk=self.instance.pk).filter(phone=phone).exists():
            raise forms.ValidationError("Phone number already in use.")
        return phone

    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if AdminLogin.objects.exclude(pk=self.instance.pk).filter(id_number=id_number).exists():
            raise forms.ValidationError("ID number already registered.")
        return id_number

    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if age < 18 or age > 80:
            raise forms.ValidationError("Age must be between 18 and 80 years.")

        return dob