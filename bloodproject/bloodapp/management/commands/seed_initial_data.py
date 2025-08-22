import json
from django.core.management.base import BaseCommand
from bloodapp.models import Marker, HealthCondition
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Seed initial Marker and HealthCondition data from JSON files.'

    def handle(self, *args, **options):
        # Load markers.json
        markers_path = os.path.join(settings.BASE_DIR, 'bloodapp', 'markers.json')
        with open(markers_path, 'r', encoding='utf-8') as f:
            markers_data = json.load(f)["markers"]

        # Seed Markers
        for marker in markers_data:
            obj, created = Marker.objects.get_or_create(
                name=marker["marker_id"],
                defaults={
                    "display_name": marker["marker_id"],
                    "background": marker["background"],
                    "discussion": marker["discussion"],
                    "standard_min": marker["ranges"]["standard_us"]["min"],
                    "standard_max": marker["ranges"]["standard_us"]["max"],
                    "optimal_min": marker["ranges"]["optimal_us"]["min"],
                    "optimal_max": marker["ranges"]["optimal_us"]["max"],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Marker: {obj.name}'))
            else:
                self.stdout.write(f'Exists Marker: {obj.name}')

        # Load health_conditions.json
        conditions_path = os.path.join(settings.BASE_DIR, 'bloodapp', 'health_conditions.json')
        with open(conditions_path, 'r', encoding='utf-8') as f:
            conditions_data = json.load(f)["health_conditions"]

        # Seed HealthConditions
        for cond in conditions_data:
            obj, created = HealthCondition.objects.get_or_create(
                condition_id=cond["condition_id"],
                defaults={
                    "display_name": cond["condition_id"].replace('_', ' ').title(),
                    "background": cond["background"],
                    "signs_and_symptoms": cond["signs_and_symptoms"],
                    "differential_diagnoses": cond["differential_diagnoses"],
                    "causes": cond["causes"],
                    "diseases": cond["diseases"],
                    "treatment": cond["treatment"],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created HealthCondition: {obj.condition_id}'))
            else:
                self.stdout.write(f'Exists HealthCondition: {obj.condition_id}')

            # Associate markers (low)
            for assoc in cond.get("associated_markers_low", []):
                marker_name = assoc["marker"]
                try:
                    marker_obj = Marker.objects.get(name=marker_name)
                    obj.associated_markers_low.add(marker_obj)
                except Marker.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Marker {marker_name} not found for low association'))

            # Associate markers (high)
            for assoc in cond.get("associated_markers_high", []):
                marker_name = assoc["marker"]
                try:
                    marker_obj = Marker.objects.get(name=marker_name)
                    obj.associated_markers_high.add(marker_obj)
                except Marker.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Marker {marker_name} not found for high association'))

        self.stdout.write(self.style.SUCCESS('Seeding complete.')) 