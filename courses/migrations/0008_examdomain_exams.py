# Generated by Django 2.1.5 on 2021-05-26 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_remove_examdomain_journeys'),
    ]

    operations = [
        migrations.AddField(
            model_name='examdomain',
            name='exams',
            field=models.ManyToManyField(blank=True, null=True, to='courses.Exam'),
        ),
    ]
