# Generated by Django 2.1.5 on 2021-08-17 04:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0075_reportederrorneousquestion_issue_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentorpaperanswerpaper',
            name='query',
            field=models.CharField(blank=True, max_length=1100, null=True),
        ),
    ]
