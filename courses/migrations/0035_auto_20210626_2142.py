# Generated by Django 2.1.5 on 2021-06-26 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0034_auto_20210623_2052'),
    ]

    operations = [
        migrations.AlterField(
            model_name='domainannouncement',
            name='text',
            field=models.CharField(max_length=500),
        ),
    ]
