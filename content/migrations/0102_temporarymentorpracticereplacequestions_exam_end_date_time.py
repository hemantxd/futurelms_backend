# Generated by Django 2.1.5 on 2021-11-29 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0101_temporarymentorpracticereplacequestions_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='temporarymentorpracticereplacequestions',
            name='exam_end_date_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='End Date and Time of the Exam'),
        ),
    ]
