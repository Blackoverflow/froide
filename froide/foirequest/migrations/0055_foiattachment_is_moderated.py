# Generated by Django 3.2.12 on 2022-06-17 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("foirequest", "0054_alter_foirequest_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="foiattachment",
            name="is_moderated",
            field=models.BooleanField(default=False, verbose_name="Has been moderated"),
        ),
    ]
