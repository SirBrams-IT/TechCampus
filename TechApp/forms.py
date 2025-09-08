from datetime import date

from django import forms
from TechApp.models import Course, Enrollment, Member,Assignment,Submission,AdminLogin, Lesson,Module


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


class AssignmentForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            mentor = AdminLogin.objects.filter(username=user.username).first()  # Avoid exception
            if mentor:
                self.fields['mentor'].queryset = AdminLogin.objects.filter(username=user.username)
                self.fields['mentor'].initial = mentor
                self.fields['mentor'].disabled = True  # Prevent modification

    class Meta:
        model = Assignment
        fields = ['title', 'description', 'file', 'due_date', 'mentor']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter assignment title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter detailed description', 'rows': 4}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = '__all__'

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['submitted_file']
        widgets = {
            'submitted_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }

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

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'learning_status']     


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description"]


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
        fields = "__all__"

    def clean_links(self):
        links_text = self.data.getlist("links[]")
        return [link.strip() for link in links_text if link.strip()] or None
