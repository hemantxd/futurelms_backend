# Generated by Django 2.1.5 on 2021-07-02 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0037_auto_20210701_1431'),
    ]

    operations = [
        migrations.AddField(
            model_name='examsuggestedbooks',
            name='title',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
