from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from bloodapp.models import Marker
import csv
import os


def parse_number(value):
	if value is None:
		return None
	s = str(value).strip()
	if not s:
		return None
	# Remove commas, percentages, and units text
	s = s.replace(',', '').replace('%', '').replace('pg/Mol', '').replace('pg/mol', '')
	try:
		return float(s)
	except ValueError:
		return None


class Command(BaseCommand):
	help = 'Import markers from Blood Reference Guide.csv into Marker model'

	def add_arguments(self, parser):
		parser.add_argument('--path', type=str, help='Path to Blood Reference Guide.csv (defaults to project root)')
		parser.add_argument('--truncate', action='store_true', help='Delete existing Markers before import')

	def handle(self, *args, **options):
		csv_path = options.get('path') or os.path.join(settings.BASE_DIR, 'Blood Reference Guide.csv')
		if not os.path.exists(csv_path):
			raise CommandError(f'CSV not found at {csv_path}')

		if options.get('truncate'):
			self.stdout.write(self.style.WARNING('Truncating Marker table...'))
			Marker.objects.all().delete()

		created_count = 0
		updated_count = 0

		with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
			reader = csv.DictReader(f)
			required = [
				'Name','Background','Discussion',
				'Low Standard Conventional','High Standard Conventional',
				'Low Standard International','High Standard International',
				'Low Optimal Conventional','High Optimal Conventional',
				'Low Optimal International','High Optimal International',
				'Standard Unit','International Units',
				'Clinical Implications Low','Clinical Implications High',
				'Other Condtions Low','Other Condtions High',
				'Interfering Factors Falsely Elevated','Interfering Factors Falsely Decreased',
				'Drug Tests','Drug Causes of Decreased Levels','Drug Causes of Increased Levels'
			]
			missing = [c for c in required if c not in reader.fieldnames]
			if missing:
				raise CommandError(f'Missing columns: {missing}')

			for row in reader:
				name = (row.get('Name') or '').strip()
				if not name:
					continue
				background = (row.get('Background') or '').strip()
				discussion = (row.get('Discussion') or '').strip()

				standard_min_conv = parse_number(row.get('Low Standard Conventional'))
				standard_max_conv = parse_number(row.get('High Standard Conventional'))
				standard_min_int = parse_number(row.get('Low Standard International'))
				standard_max_int = parse_number(row.get('High Standard International'))
				optimal_min_conv = parse_number(row.get('Low Optimal Conventional'))
				optimal_max_conv = parse_number(row.get('High Optimal Conventional'))
				optimal_min_int = parse_number(row.get('Low Optimal International'))
				optimal_max_int = parse_number(row.get('High Optimal International'))

				standard_unit = (row.get('Standard Unit') or '').strip() or None
				international_unit = (row.get('International Units') or '').strip() or None

				clinical_low = (row.get('Clinical Implications Low') or '').strip() or None
				clinical_high = (row.get('Clinical Implications High') or '').strip() or None
				other_low = (row.get('Other Condtions Low') or '').strip() or None
				other_high = (row.get('Other Condtions High') or '').strip() or None
				interf_high = (row.get('Interfering Factors Falsely Elevated') or '').strip() or None
				interf_low = (row.get('Interfering Factors Falsely Decreased') or '').strip() or None
				drug_tests = (row.get('Drug Tests') or '').strip() or None
				drug_dec = (row.get('Drug Causes of Decreased Levels') or '').strip() or None
				drug_inc = (row.get('Drug Causes of Increased Levels') or '').strip() or None

				# Backward compatibility for display_name and consolidated ranges
				display_name = name
				standard_min = standard_min_conv if standard_min_conv is not None else (standard_min_int or 0)
				standard_max = standard_max_conv if standard_max_conv is not None else (standard_max_int or 0)
				optimal_min = optimal_min_conv if optimal_min_conv is not None else (optimal_min_int or 0)
				optimal_max = optimal_max_conv if optimal_max_conv is not None else (optimal_max_int or 0)

				obj, created = Marker.objects.update_or_create(
					name=name,
					defaults={
						'display_name': display_name,
						'background': background,
						'discussion': discussion,
						'standard_min': standard_min,
						'standard_max': standard_max,
						'optimal_min': optimal_min,
						'optimal_max': optimal_max,
						'standard_unit': standard_unit,
						'international_unit': international_unit,
						'standard_min_conventional': standard_min_conv,
						'standard_max_conventional': standard_max_conv,
						'optimal_min_conventional': optimal_min_conv,
						'optimal_max_conventional': optimal_max_conv,
						'standard_min_international': standard_min_int,
						'standard_max_international': standard_max_int,
						'optimal_min_international': optimal_min_int,
						'optimal_max_international': optimal_max_int,
						'clinical_implications_low': clinical_low,
						'clinical_implications_high': clinical_high,
						'other_conditions_low': other_low,
						'other_conditions_high': other_high,
						'interfering_factors_falsely_elevated': interf_high,
						'interfering_factors_falsely_decreased': interf_low,
						'drug_tests': drug_tests,
						'drug_causes_decreased': drug_dec,
						'drug_causes_increased': drug_inc,
					}
				)

				if created:
					created_count += 1
				else:
					updated_count += 1

		self.stdout.write(self.style.SUCCESS(f'Import completed: {created_count} created, {updated_count} updated')) 