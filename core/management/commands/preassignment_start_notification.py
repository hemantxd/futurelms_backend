from django.core.management.base import BaseCommand
from enrolledpackages import tasks as enrolledpackages_tasks


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('preassignment_start_notification started'))
        enrolledpackages_tasks.preassignment_start_notification()
        self.stdout.write(self.style.SUCCESS('preassignment_start_notification completed'))
