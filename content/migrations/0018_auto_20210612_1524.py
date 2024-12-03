# Generated by Django 2.1.5 on 2021-06-12 09:54

import ckeditor_uploader.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0017_auto_20210612_1156'),
    ]

    operations = [
        migrations.CreateModel(
            name='FillUpWithOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('text', ckeditor_uploader.fields.RichTextUploadingField(blank=True, null=True, verbose_name='text')),
                ('correct', models.BooleanField(default=False)),
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
            field=models.CharField(choices=[('mcq', 'Single Correct Choice'), ('mcc', 'Multiple Correct Choice'), ('fillup', 'Fill In The Blanks'), ('subjective', 'Subjective type'), ('numerical', 'Numerical'), ('assertion', 'Assertion'), ('boolean', 'True False'), ('fillup_option', 'Fill With Option')], max_length=24),
        ),
    ]
