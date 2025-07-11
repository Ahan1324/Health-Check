from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Marker, HealthCondition, BloodTestReport, MarkerReading

admin.site.register(Marker)
admin.site.register(HealthCondition)
admin.site.register(BloodTestReport)
admin.site.register(MarkerReading)