# Generated by Django 2.1.5 on 2022-09-21 07:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0020_remove_profile_syllabus'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='adhar_no',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='dob',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='father_name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='sr_number',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='whats_app',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
