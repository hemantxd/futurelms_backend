# Generated by Django 2.1.5 on 2021-09-04 06:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0085_auto_20210830_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='sharedpapers',
            name='shared_by_me_paper_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sharedpapers',
            name='shared_to_me_paper_count',
            field=models.IntegerField(default=0),
        ),
    ]
