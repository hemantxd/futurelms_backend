# Generated by Django 2.1.5 on 2021-10-09 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0092_auto_20211009_1234'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='update_code',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
