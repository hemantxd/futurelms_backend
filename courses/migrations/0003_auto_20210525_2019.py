# Generated by Django 2.1.5 on 2021-05-25 14:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_journeynode_pathnodes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pathnodes',
            name='domain',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.ExamDomain'),
        ),
    ]
