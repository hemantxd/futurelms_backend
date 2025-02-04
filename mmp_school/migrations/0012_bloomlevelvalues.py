# Generated by Django 2.1.5 on 2023-02-10 07:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mmp_school', '0011_auto_20230208_1130'),
    ]

    operations = [
        migrations.CreateModel(
            name='BloomLevelValues',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('memory_based', models.IntegerField(blank=True, default=0, null=True)),
                ('conceptual', models.IntegerField(blank=True, default=0, null=True)),
                ('application', models.IntegerField(blank=True, default=0, null=True)),
                ('analyze', models.IntegerField(blank=True, default=0, null=True)),
                ('evaluate', models.IntegerField(blank=True, default=0, null=True)),
                ('unique_values', models.CharField(blank=True, max_length=20, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
