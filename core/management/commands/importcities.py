from django.core.management.base import BaseCommand
from django.conf import settings
import os
import csv
from countrystatecity import models as countrystatecity_models

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('import cities started'))
        with open(os.path.join(settings.BASE_DIR, 'cities.csv')) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                state_id = countrystatecity_models.States.objects.get(name=row[3])
                countrystatecity_models.Cities.objects.create(name=row[1], state=state_id)        
        self.stdout.write(self.style.SUCCESS('import cities completed'))
