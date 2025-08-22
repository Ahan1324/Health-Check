from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class BloodTestForm(forms.Form):
    patient_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter patient name'})
    )
    
    # Blood count
    hemoglobin = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 14.0', 'step': '0.1'})
    )
    white_blood_cells = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 7.5', 'step': '0.1'})
    )
    platelets = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 250', 'step': '1'})
    )
    
    # Electrolytes
    sodium = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 140', 'step': '0.1'})
    )
    potassium = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 4.0', 'step': '0.1'})
    )
    chloride = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 102', 'step': '0.1'})
    )
    carbon_dioxide = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 24', 'step': '0.1'})
    )
    
    # Kidney function
    blood_urea_nitrogen = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 15', 'step': '0.1'})
    )
    creatinine = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1.0', 'step': '0.01'})
    )
    
    # Glucose
    glucose = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 95', 'step': '0.1'})
    )
    
    # Minerals
    calcium = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 9.5', 'step': '0.1'})
    )
    
    # Proteins
    total_protein = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 7.0', 'step': '0.1'})
    )
    albumin = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 4.0', 'step': '0.1'})
    )
    
    # Liver function
    total_bilirubin = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0.8', 'step': '0.1'})
    )
    alkaline_phosphatase = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 70', 'step': '0.1'})
    )
    alt = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 25', 'step': '0.1'})
    )
    ast = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 24', 'step': '0.1'})
    )
    
    # Lipids
    total_cholesterol = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 180', 'step': '0.1'})
    )
    hdl_cholesterol = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 55', 'step': '0.1'})
    )
    ldl_cholesterol = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 100', 'step': '0.1'})
    )
    triglycerides = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 120', 'step': '0.1'})
    )
    
    # Hormones
    tsh = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2.5', 'step': '0.01'})
    )
    
    # Vitamins and minerals
    vitamin_d = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 30', 'step': '0.1'})
    )
    ferritin = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 80', 'step': '0.1'})
    )
    iron = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 90', 'step': '0.1'})
    )
    tibc = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 300', 'step': '0.1'})
    )
    folate = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8.0', 'step': '0.1'})
    )
    b12 = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 500', 'step': '0.1'})
    )
    magnesium = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2.0', 'step': '0.1'})
    )
    zinc = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 80', 'step': '0.1'})
    )
    copper = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 100', 'step': '0.1'})
    )
    selenium = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 120', 'step': '0.1'})
    )
    
    # Inflammatory markers
    crp = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2.0', 'step': '0.1'})
    )
    homocysteine = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8.0', 'step': '0.1'})
    )

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes and placeholders
        self.fields['username'].label = "Username"
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['email'].label = "Email"
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'you@example.com'
        })
        self.fields['password1'].label = "Password"
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].label = "Confirm Password"
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Re-enter your password'
        })

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
