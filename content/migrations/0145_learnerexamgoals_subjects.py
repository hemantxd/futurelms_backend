# Generated by Django 2.1.5 on 2022-04-14 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0078_selfassessexamquestions_is_compulsory'),
        ('content', '0144_auto_20220413_1631'),
    ]

    operations = [
        migrations.AddField(
            model_name='learnerexamgoals',
            name='subjects',
            field=models.ManyToManyField(blank=True, null=True, to='courses.Subject'),
        ),
    ]
