from django import forms

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
