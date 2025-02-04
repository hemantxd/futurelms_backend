# Generated by Django 2.1.5 on 2021-06-02 06:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0005_remove_question_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='FillUpSolution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('text', models.CharField(blank=True, max_length=100, null=True)),
                ('questioncontent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='content.QuestionContent')),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='question',
            name='type_of_question',
            field=models.CharField(choices=[('mcq', 'Single Correct Choice'), ('mcc', 'Multiple Correct Choice'), ('fillup', 'Fill In The Blanks'), ('subjective', 'Subjective type')], max_length=24),
        ),
    ]
