from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from bloodapp.models import HealthCondition
import csv
import os
import re


def to_condition_id(s: str) -> str:
	base = (s or '').strip().lower()
	# replace any non-alphanumeric with underscore, collapse repeats, trim
	base = re.sub(r'[^a-z0-9]+', '_', base)
	base = re.sub(r'_+', '_', base).strip('_')
	return base


class Command(BaseCommand):
	help = 'Import clinical conditions from Clinical Conditions.csv into HealthCondition model'

	def add_arguments(self, parser):
		parser.add_argument('--path', type=str, help='Path to the CSV file (defaults to project root Clinical Conditions.csv)')
		parser.add_argument('--truncate', action='store_true', help='Delete existing HealthCondition rows before import')

	def handle(self, *args, **options):
		csv_path = options.get('path') or os.path.join(settings.BASE_DIR, 'Clinical Conditions.csv')
		if not os.path.exists(csv_path):
			raise CommandError(f'CSV not found at {csv_path}')

		if options.get('truncate'):
			self.stdout.write(self.style.WARNING('Truncating HealthCondition table...'))
			HealthCondition.objects.all().delete()

		created_count = 0
		updated_count = 0

		with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
			reader = csv.DictReader(f)
			# Allow either legacy 's/sx' or new 's/sx bullet' column
			required_base = ['Name', 'Background', 'dx', 'causes', 'dzs', 'Treatments']
			missing = [c for c in required_base if c not in reader.fieldnames]
			if missing:
				raise CommandError(f"Missing required columns: {missing}. Found columns: {reader.fieldnames}")
			if ('s/sx' not in reader.fieldnames) and ('s/sx bullet' not in reader.fieldnames):
				raise CommandError("Missing required column: either 's/sx' or 's/sx bullet' must be present.")

			for row in reader:
				name = (row.get('Name') or '').strip()
				background = (row.get('Background') or '').strip()
				# Prefer the new bullet column if present
				bullets_raw = (row.get('s/sx bullet') or '').strip()
				legacy_sx = (row.get('s/sx') or '').strip()
				if bullets_raw:
					parts = [p.strip() for p in re.split(r'«', bullets_raw) if p and p.strip()]
					# Store as newline-separated bullets so downstream quiz parser can render them
					signs_and_symptoms = '\n'.join(f'• {p}' for p in parts)
				else:
					signs_and_symptoms = legacy_sx
				diagnosis = (row.get('dx') or '').strip()
				causes = (row.get('causes') or '').strip()
				diseases = (row.get('dzs') or '').strip()
				treatments = (row.get('Treatments') or '').strip()

				if not name:
					# skip empty rows
					continue

				display_name = name
				condition_id = to_condition_id(name)

				obj, created = HealthCondition.objects.update_or_create(
					name=name,
					defaults={
						'display_name': display_name,
						'condition_id': condition_id,
						'background': background or None,
						'signs_and_symptoms': signs_and_symptoms or None,
						'diagnosis': diagnosis or None,
						'causes': causes or None,
						'diseases': diseases or None,
						'treatments': treatments or None,
					}
				)
				if created:
					created_count += 1
				else:
					updated_count += 1

		self.stdout.write(self.style.SUCCESS(f'Import completed: {created_count} created, {updated_count} updated')) 