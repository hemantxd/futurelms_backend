# Generated by Django 2.1.5 on 2022-03-02 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0075_selfassessquestionbank'),
    ]

    operations = [
        migrations.AddField(
            model_name='domainannouncement',
            name='order',
            field=models.IntegerField(default=100),
        ),
    ]
