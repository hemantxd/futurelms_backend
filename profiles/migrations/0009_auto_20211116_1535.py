# Generated by Django 2.1.5 on 2021-11-16 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0008_auto_20211109_1126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='last_name',
            field=models.TextField(blank=True, null=True),
        ),
    ]
