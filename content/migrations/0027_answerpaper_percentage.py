# Generated by Django 2.1.5 on 2021-06-25 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0026_auto_20210625_1448'),
    ]

    operations = [
        migrations.AddField(
            model_name='answerpaper',
            name='percentage',
            field=models.IntegerField(default=0, verbose_name='Total Percentage'),
        ),
    ]
