# Generated by Django 2.1.5 on 2022-03-16 04:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0135_auto_20220315_2226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learnerexamgoals',
            name='last_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
