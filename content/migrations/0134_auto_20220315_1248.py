# Generated by Django 2.1.5 on 2022-03-15 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0133_auto_20220315_1235'),
    ]

    operations = [
        migrations.AddField(
            model_name='goalassessmentexamanswerpaper',
            name='marks',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name='goalassessmentexamanswerpaper',
            name='score',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
    ]
