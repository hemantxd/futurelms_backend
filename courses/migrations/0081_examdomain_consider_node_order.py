# Generated by Django 2.1.5 on 2022-05-23 12:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0080_pathnodes_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='examdomain',
            name='consider_node_order',
            field=models.BooleanField(default=False),
        ),
    ]
