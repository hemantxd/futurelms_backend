# Generated by Django 2.1.5 on 2021-07-14 07:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0050_question_languages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useranswer',
            name='user_boolean_answer',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
