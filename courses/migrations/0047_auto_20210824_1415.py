# Generated by Django 2.1.5 on 2021-08-24 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0046_examsuggestedbooks_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
