# Generated by Django 2.1.5 on 2022-09-30 12:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0162_auto_20220930_1715'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instituteclassroom',
            name='institute',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='profiles.Institute'),
        ),
    ]
