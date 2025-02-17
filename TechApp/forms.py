from datetime import date

from django import forms
from TechApp.models import FileModel, Member,Assignment,Submission,AdminLogin


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileModel
        fields = ['file', 'video', 'course_name', 'course_code', 'instructor', 'zoom_link', 'google_classroom_link']
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Course Name'}),
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Course Code'}),
            'instructor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Instructor Name'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'zoom_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter Zoom Link'}),
            'google_classroom_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter Google Classroom Link'}),
        }

class StudentForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email', 'username', 'phone', 'id_number', 'date_of_birth', 'gender', 'profile_image']

    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)

        # Make specific fields read-only
        self.fields['id_number'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['phone'].widget.attrs['readonly'] = True
        self.fields['username'].widget.attrs['readonly'] = True

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