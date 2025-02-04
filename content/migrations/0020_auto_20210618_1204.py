# Generated by Django 2.1.5 on 2021-06-18 06:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0019_answerpaper_useranswer'),
    ]

    operations = [
        migrations.AddField(
            model_name='useranswer',
            name='correct_fillup_answer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='correct_fillup_answer', to='content.FillUpSolution'),
        ),
        migrations.AddField(
            model_name='useranswer',
            name='correct_fillup_option_answer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='correct_fillup_option_answer', to='content.FillUpWithOption'),
        ),
    ]
