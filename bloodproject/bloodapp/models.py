from django.db import models

# Create your models here.

from django.contrib.auth.models import User
from django.db import models

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.user.username


class Marker(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    background = models.TextField()
    discussion = models.TextField()
    standard_min = models.FloatField()
    standard_max = models.FloatField()
    optimal_min = models.FloatField()
    optimal_max = models.FloatField()

    def __str__(self):
        return self.display_name

class BloodTestReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.upload_date.date()}"


class BloodTestReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.upload_date.date()}"



class MarkerReading(models.Model):
    report = models.ForeignKey(BloodTestReport, on_delete=models.CASCADE, related_name='readings')
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    value = models.FloatField()
    units = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.marker.display_name}: {self.value}"


class HealthCondition(models.Model):
    condition_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    background = models.TextField()
    signs_and_symptoms = models.JSONField()
    differential_diagnoses = models.JSONField()
    causes = models.JSONField()
    diseases = models.JSONField()
    treatment = models.TextField()

    associated_markers_low = models.ManyToManyField(Marker, related_name='low_conditions', blank=True)
    associated_markers_high = models.ManyToManyField(Marker, related_name='high_conditions', blank=True)

    def __str__(self):
        return self.display_name


class ReportConditionSuggestion(models.Model):
    report = models.ForeignKey(BloodTestReport, on_delete=models.CASCADE, related_name='condition_suggestions')
    condition = models.ForeignKey(HealthCondition, on_delete=models.CASCADE)
    confidence_score = models.FloatField(default=0.0)  # Optional: % match or LLM certainty
    rationale = models.TextField(blank=True)  # Why this condition was matched

    def __str__(self):
        return f"{self.condition.display_name} for {self.report}"


class SymptomResponse(models.Model):
    suggestion = models.ForeignKey(ReportConditionSuggestion, on_delete=models.CASCADE, related_name='symptom_responses')
    symptom_name = models.CharField(max_length=255)
    response = models.CharField(max_length=3, choices=[('yes', 'Yes'), ('no', 'No')])
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.symptom_name}: {self.response}"
