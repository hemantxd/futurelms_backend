# Generated by Django 2.1.5 on 2021-07-09 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0042_auto_20210709_1243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learnerexampapersubjects',
            name='chapters',
            field=models.ManyToManyField(blank=True, null=True, to='content.LearnerExamPaperChapters'),
        ),
        migrations.AlterField(
            model_name='learnerexampracticesubjects',
            name='chapters',
            field=models.ManyToManyField(blank=True, null=True, to='content.LearnerExamPracticeChapters'),
        ),
    ]
