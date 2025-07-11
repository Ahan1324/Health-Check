from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class BloodTestForm(forms.Form):
    patient_name = forms.CharField(max_length=100)
    Ferritin = forms.FloatField()
    CRP = forms.FloatField()
    TSH = forms.FloatField()
    Vitamin_D = forms.FloatField()
    Homocysteine = forms.FloatField()
    LDL = forms.FloatField()
    ALT = forms.FloatField()
    Creatinine = forms.FloatField()
    WBC = forms.FloatField()
    HbA1c = forms.FloatField()
    # You can add more fields as needed

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
