# Generated by Django 2.1.5 on 2022-05-09 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0154_auto_20220509_1739'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='learnerpapers',
            name='paper_id',
        ),
        migrations.AddField(
            model_name='learnerpapers',
            name='path_id',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
