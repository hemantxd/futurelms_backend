# Generated by Django 2.1.5 on 2021-07-06 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0033_auto_20210701_1019'),
    ]

    operations = [
        migrations.AddField(
            model_name='questioncontent',
            name='hint',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]
