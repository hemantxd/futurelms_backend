# Generated by Django 2.1.5 on 2021-06-12 06:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0028_auto_20210612_1117'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ExamAverageMarksPerQuestion',
            new_name='ExamAverageTimePerQuestion',
        ),
    ]
