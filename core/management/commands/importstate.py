from django.core.management.base import BaseCommand
from django.conf import settings
import os
import csv
from countrystatecity import models as countrystatecity_models

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('import state started'))
        with open(os.path.join(settings.BASE_DIR, 'states.csv')) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                country_id = countrystatecity_models.Countries.objects.get(name=row[3])
                countrystatecity_models.States.objects.create(name=row[1], country=country_id)        
        self.stdout.write(self.style.SUCCESS('import state completed'))
