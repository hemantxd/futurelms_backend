# Generated by Django 2.1.5 on 2022-04-26 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0148_studentinstitutechangeinvitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='learnerexamgoals',
            name='count',
            field=models.IntegerField(default=0),
        ),
    ]
