# Generated by Django 2.1.5 on 2021-12-13 06:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0066_auto_20211207_1307'),
        ('content', '0106_selfassessexamanswerpaper_selfassessuseranswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChapterMasterFTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chapter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.Chapter')),
                ('questions', models.ManyToManyField(blank=True, null=True, to='content.Question')),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
    ]
