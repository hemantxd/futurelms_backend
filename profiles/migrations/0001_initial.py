# Generated by Django 2.1.5 on 2021-05-25 13:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import profiles.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('countrystatecity', '0001_initial'),
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.TextField(blank=True)),
                ('last_name', models.TextField(blank=True)),
                ('address', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, upload_to=profiles.models.image_upload_to)),
                ('contact_verified', models.BooleanField(default=False)),
                ('rollno', models.TextField(blank=True)),
                ('pincode', models.IntegerField(blank=True, null=True)),
                ('complete_profile', models.BooleanField(default=False)),
                ('city', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='countrystatecity.Cities')),
                ('state', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='countrystatecity.States')),
                ('studentBoard', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.UserBoard')),
                ('studentClass', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.UserClass')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('user_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.UserGroup')),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
    ]
