# Generated by Django 2.1.5 on 2021-08-25 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0047_auto_20210824_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainannouncement',
            name='last_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
