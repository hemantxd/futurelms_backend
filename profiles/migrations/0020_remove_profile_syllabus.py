# Generated by Django 2.1.5 on 2022-04-07 07:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0019_auto_20220407_1324'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='syllabus',
        ),
    ]
