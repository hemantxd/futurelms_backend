# Generated by Django 2.1.5 on 2021-06-08 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0011_auto_20210608_1750'),
    ]

    operations = [
        migrations.AddField(
            model_name='learnerhistory',
            name='papers',
            field=models.ManyToManyField(blank=True, null=True, to='content.LearnerPapers'),
        ),
    ]
