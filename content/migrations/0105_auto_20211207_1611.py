# Generated by Django 2.1.5 on 2021-12-07 10:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0104_learnerexamgoals'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learnerexamgoals',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
