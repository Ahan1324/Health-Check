from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from bloodapp.models import HealthCondition, Marker


class Command(BaseCommand):
    help = 'Manage associated markers for health conditions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['list', 'add', 'remove', 'clear', 'set-expert-comment'],
            default='list',
            help='Action to perform: list, add, remove, clear markers, or set expert comment'
        )
        parser.add_argument(
            '--condition',
            type=str,
            help='Health condition name or ID'
        )
        parser.add_argument(
            '--markers',
            nargs='+',
            help='Marker names to add/remove'
        )
        parser.add_argument(
            '--type',
            choices=['low', 'high'],
            help='Type of marker association (low or high) - not used for expert comments'
        )
        parser.add_argument(
            '--expert-comment',
            type=str,
            help='Expert comment text for marker importance'
        )

    def handle(self, *args, **options):
        action = options['action']
        condition_name = options['condition']
        markers = options['markers'] or []
        marker_type = options['type']

        if action == 'list':
            self.list_conditions()
        elif action in ['add', 'remove', 'clear']:
            if not condition_name:
                raise CommandError('--condition is required for add/remove/clear actions')
            if action in ['add', 'remove'] and not markers:
                raise CommandError('--markers is required for add/remove actions')
            if action in ['add', 'remove'] and not marker_type:
                raise CommandError('--type is required for add/remove actions')
            
            self.modify_markers(action, condition_name, markers, marker_type)
        elif action == 'set-expert-comment':
            if not condition_name:
                raise CommandError('--condition is required for set-expert-comment action')
            if not options.get('expert_comment'):
                raise CommandError('--expert-comment is required for set-expert-comment action')
            
            self.set_expert_comment(condition_name, options['expert_comment'])

    def list_conditions(self):
        """List all health conditions with their associated markers"""
        conditions = HealthCondition.objects.all()
        
        if not conditions.exists():
            self.stdout.write(self.style.WARNING('No health conditions found.'))
            return

        for condition in conditions:
            self.stdout.write(f"\n{self.style.SUCCESS(condition.name or condition.condition_id)}:")
            
            low_markers = condition.associated_markers_low.all()
            high_markers = condition.associated_markers_high.all()
            
            if low_markers.exists():
                self.stdout.write(f"  Low markers: {', '.join([m.name for m in low_markers])}")
            else:
                self.stdout.write("  Low markers: None")
                
            if high_markers.exists():
                self.stdout.write(f"  High markers: {', '.join([m.name for m in high_markers])}")
            else:
                self.stdout.write("  High markers: None")
            
            if condition.expert_comment_markers:
                self.stdout.write(f"  Expert comment: {condition.expert_comment_markers[:100]}...")

    def modify_markers(self, action, condition_name, marker_names, marker_type):
        """Add, remove, or clear markers for a health condition"""
        try:
            # Try to find condition by name or condition_id
            condition = HealthCondition.objects.filter(
                name__icontains=condition_name
            ).first() or HealthCondition.objects.filter(
                condition_id__icontains=condition_name
            ).first()
            
            if not condition:
                raise CommandError(f'Health condition "{condition_name}" not found')

            # Get the appropriate marker field
            if marker_type == 'low':
                marker_field = condition.associated_markers_low
            else:
                marker_field = condition.associated_markers_high

            with transaction.atomic():
                if action == 'add':
                    self.add_markers(condition, marker_field, marker_names, marker_type)
                elif action == 'remove':
                    self.remove_markers(condition, marker_field, marker_names, marker_type)
                elif action == 'clear':
                    self.clear_markers(condition, marker_field, marker_type)

        except Exception as e:
            raise CommandError(f'Error modifying markers: {str(e)}')

    def add_markers(self, condition, marker_field, marker_names, marker_type):
        """Add markers to a health condition"""
        markers_to_add = []
        not_found = []
        
        for marker_name in marker_names:
            marker = Marker.objects.filter(name__icontains=marker_name).first()
            if marker:
                markers_to_add.append(marker)
            else:
                not_found.append(marker_name)
        
        if markers_to_add:
            marker_field.add(*markers_to_add)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Added {len(markers_to_add)} {marker_type} marker(s) to "{condition.name}": '
                    f'{", ".join([m.name for m in markers_to_add])}'
                )
            )
        
        if not_found:
            self.stdout.write(
                self.style.WARNING(
                    f'Markers not found: {", ".join(not_found)}'
                )
            )

    def remove_markers(self, condition, marker_field, marker_names, marker_type):
        """Remove markers from a health condition"""
        markers_to_remove = []
        not_found = []
        
        for marker_name in marker_names:
            marker = Marker.objects.filter(name__icontains=marker_name).first()
            if marker:
                markers_to_remove.append(marker)
            else:
                not_found.append(marker_name)
        
        if markers_to_remove:
            marker_field.remove(*markers_to_remove)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Removed {len(markers_to_remove)} {marker_type} marker(s) from "{condition.name}": '
                    f'{", ".join([m.name for m in markers_to_remove])}'
                )
            )
        
        if not_found:
            self.stdout.write(
                self.style.WARNING(
                    f'Markers not found: {", ".join(not_found)}'
                )
            )

    def clear_markers(self, condition, marker_field, marker_type):
        """Clear all markers of a specific type from a health condition"""
        count = marker_field.count()
        marker_field.clear()
        self.stdout.write(
            self.style.SUCCESS(
                f'Cleared {count} {marker_type} marker(s) from "{condition.name}"'
            )
        )

    def set_expert_comment(self, condition_name, comment):
        """Set expert comment for a health condition's markers"""
        try:
            # Try to find condition by name or condition_id
            condition = HealthCondition.objects.filter(
                name__icontains=condition_name
            ).first() or HealthCondition.objects.filter(
                condition_id__icontains=condition_name
            ).first()
            
            if not condition:
                raise CommandError(f'Health condition "{condition_name}" not found')

            with transaction.atomic():
                condition.expert_comment_markers = comment
                condition.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Set expert comment for "{condition.name}": {comment[:100]}...'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error setting expert comment: {str(e)}')
