from django.contrib import admin
from .models import Marker, HealthCondition, BloodTestReport, MarkerReading

class MarkerAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'standard_min', 'standard_max', 'standard_unit']
    search_fields = ['name', 'display_name']
    list_filter = ['standard_unit']

class HealthConditionAdmin(admin.ModelAdmin):
    list_display = ['name', 'condition_id', 'display_name']
    search_fields = ['name', 'condition_id', 'display_name']
    filter_horizontal = ['associated_markers_low', 'associated_markers_high']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'condition_id', 'display_name')
        }),
        ('Description', {
            'fields': ('background', 'signs_and_symptoms', 'diagnosis', 'causes', 'diseases', 'treatments')
        }),
        ('Associated Markers', {
            'fields': ('associated_markers_low', 'associated_markers_high'),
            'description': 'Select markers that are typically low or high in this health condition'
        }),
        ('Expert Commentary', {
            'fields': ('expert_comment_markers',),
            'description': 'IFM CP functional medicine practitioner comments on marker importance for risk assessment'
        }),
        ('Legacy Data', {
            'fields': ('differential_diagnoses',),
            'classes': ('collapse',)
        })
    )

admin.site.register(Marker, MarkerAdmin)
admin.site.register(HealthCondition, HealthConditionAdmin)
admin.site.register(BloodTestReport)
admin.site.register(MarkerReading)