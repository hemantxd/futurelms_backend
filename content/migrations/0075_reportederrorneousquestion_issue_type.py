# Generated by Django 2.1.5 on 2021-08-12 06:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0074_mentorpaperanswerpaper_submitted'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportederrorneousquestion',
            name='issue_type',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
