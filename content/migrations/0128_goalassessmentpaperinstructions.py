# Generated by Django 2.1.5 on 2022-03-15 05:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0127_auto_20220315_1120'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoalAssessmentPaperInstructions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('instruction', models.CharField(blank=True, max_length=200, null=True)),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='content.GoalAssessmentExamAnswerPaper')),
            ],
            options={
                'ordering': ['-created_at', '-updated_at'],
                'abstract': False,
            },
        ),
    ]
