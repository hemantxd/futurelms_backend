# Generated by Django 2.1.5 on 2023-02-25 07:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0083_auto_20220921_1321'),
        ('content', '0167_auto_20221111_1543'),
        ('mmp_school', '0012_bloomlevelvalues'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloomlevelvalues',
            name='exam',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.Exam'),
        ),
        migrations.AddField(
            model_name='bloomlevelvalues',
            name='papers',
            field=models.ManyToManyField(blank=True, null=True, to='content.LearnerPapers'),
        ),
    ]
