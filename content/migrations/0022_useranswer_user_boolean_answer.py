# Generated by Django 2.1.5 on 2021-06-18 07:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0021_useranswer_correct_boolean_answer'),
    ]

    operations = [
        migrations.AddField(
            model_name='useranswer',
            name='user_boolean_answer',
            field=models.BooleanField(default=False),
        ),
    ]
