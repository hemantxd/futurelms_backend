# Generated by Django 2.1.5 on 2023-02-08 06:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mmp_school', '0010_barbloomlevel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='barbloomlevel',
            name='title',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='courses.BloomLevel'),
        ),
    ]
