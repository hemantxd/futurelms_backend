# Generated by Django 2.1.5 on 2021-05-29 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0017_remove_chapter_exam'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chapter',
            name='chapter_order',
            field=models.IntegerField(blank=True),
        ),
    ]
