# Generated by Django 2.1.5 on 2022-03-15 05:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0121_goalassessmentexamanswerpaper_started'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='temporarypapersubjectquestiondistribution',
            name='goal_paper',
        ),
    ]
