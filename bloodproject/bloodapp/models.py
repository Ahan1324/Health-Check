from django.db import models

# Create your models here.

from django.contrib.auth.models import User
from django.db import models

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], blank=True)
    notes = models.TextField(blank=True)
    current_stage = models.CharField(
        max_length=20,
        choices=[
            ('patient_info', 'Submit Patient Info'),
            ('health_concerns', 'View Health Concerns'),
            ('treatment_plans', 'View Treatment Plans'),
            ('completed', 'Completed')
        ],
        default='patient_info'
    )

    # Legacy/progress fields present in DB
    patient_info_completed = models.BooleanField(default=False)
    blood_results_completed = models.BooleanField(default=False)
    health_concerns_completed = models.BooleanField(default=False)
    treatment_plan_completed = models.BooleanField(default=False)

    blood_analysis_results = models.JSONField(null=True, blank=True)
    health_concerns_results = models.JSONField(null=True, blank=True)
    treatment_plan_results = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.user.username


class AIAnalysisResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stage = models.CharField(max_length=20, choices=[
        ('patient_info', 'Patient Info Analysis'),
        ('health_concerns', 'Health Concerns Analysis'),
        ('treatment_plans', 'Treatment Plans Analysis')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    analysis_data = models.JSONField()  # Store the AI analysis results
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'stage']

    def __str__(self):
        return f"{self.user.username} - {self.stage}"


class Marker(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    background = models.TextField()
    discussion = models.TextField()
    
    # Existing consolidated ranges (kept for compatibility; mapped from conventional values)
    standard_min = models.FloatField()
    standard_max = models.FloatField()
    optimal_min = models.FloatField()
    optimal_max = models.FloatField()

    # Units
    standard_unit = models.CharField(max_length=64, null=True, blank=True)
    international_unit = models.CharField(max_length=64, null=True, blank=True)

    # Detailed conventional ranges
    standard_min_conventional = models.FloatField(null=True, blank=True)
    standard_max_conventional = models.FloatField(null=True, blank=True)
    optimal_min_conventional = models.FloatField(null=True, blank=True)
    optimal_max_conventional = models.FloatField(null=True, blank=True)

    # Detailed international ranges
    standard_min_international = models.FloatField(null=True, blank=True)
    standard_max_international = models.FloatField(null=True, blank=True)
    optimal_min_international = models.FloatField(null=True, blank=True)
    optimal_max_international = models.FloatField(null=True, blank=True)

    # Narrative fields from CSV
    clinical_implications_low = models.TextField(null=True, blank=True)
    clinical_implications_high = models.TextField(null=True, blank=True)
    other_conditions_low = models.TextField(null=True, blank=True)
    other_conditions_high = models.TextField(null=True, blank=True)
    interfering_factors_falsely_elevated = models.TextField(null=True, blank=True)
    interfering_factors_falsely_decreased = models.TextField(null=True, blank=True)
    drug_tests = models.TextField(null=True, blank=True)
    drug_causes_decreased = models.TextField(null=True, blank=True)
    drug_causes_increased = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.display_name

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
    name = models.CharField(max_length=200, unique=True, null=True, blank=True)
    background = models.TextField(null=True, blank=True)
    signs_and_symptoms = models.TextField(null=True, blank=True)  # s/sx field from CSV
    diagnosis = models.TextField(null=True, blank=True)  # dx field from CSV
    causes = models.TextField(null=True, blank=True)
    diseases = models.TextField(null=True, blank=True)  # dzs field from CSV
    treatments = models.TextField(null=True, blank=True)  # Treatments field from CSV

    # Legacy fields for backward compatibility
    condition_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=150, null=True, blank=True)
    differential_diagnoses = models.JSONField(null=True, blank=True)
    associated_markers_low = models.ManyToManyField(Marker, related_name='low_conditions', blank=True)
    associated_markers_high = models.ManyToManyField(Marker, related_name='high_conditions', blank=True)
    
    # Expert comments from IFM CP functional medicine practitioner
    expert_comment_markers = models.TextField(
        null=True, 
        blank=True,
        help_text="Expert commentary on which markers are most/least important for risk assessment"
    )

    def __str__(self):
        return self.name or self.display_name or (self.condition_id or 'Health Condition')


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


class RiskComputationTask(models.Model):
    """Tracks background risk score computations per condition per user."""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('error', 'Error'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    condition_id = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='queued')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'condition_id', 'status']),
        ]

    def __str__(self):
        return f"Task({self.user.username}, {self.condition_id}, {self.status})"
