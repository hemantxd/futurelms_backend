# Generated by Django 2.1.5 on 2022-09-30 09:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('mmp_school', '0001_initial'),
        ('content', '0160_instituteclassroom_room_teacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='grade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='gradename', to='core.UserClass'),
        ),
        migrations.AddField(
            model_name='instituteclassroom',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='branchname', to='mmp_school.BranchSchool'),
        ),
    ]
