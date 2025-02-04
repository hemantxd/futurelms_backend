# Generated by Django 2.1.5 on 2022-03-11 07:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0013_auto_20220310_1936'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
        ('content', '0115_temporarymentoractualpaperreplacequestions_show_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstituteClassRoom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('grade', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='core.UserClass')),
                ('institute', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='profiles.Institute')),
            ],
        ),
        migrations.CreateModel(
            name='UserClassRoom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('institute_rooms', models.ManyToManyField(blank=True, null=True, to='content.InstituteClassRoom')),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
