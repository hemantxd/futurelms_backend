# Generated by Django 2.1.5 on 2021-06-01 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0003_question_linked_topics'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='text',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
