# Generated by Django 2.1.5 on 2021-12-23 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0066_auto_20211207_1307'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='allow_goal',
            field=models.BooleanField(default=False),
        ),
    ]
