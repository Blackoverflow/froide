# Generated by Django 4.2.14 on 2024-08-27 13:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publicbody", "0049_alter_publicbody_email"),
    ]

    operations = [
        migrations.AlterField(
            model_name="publicbody",
            name="email",
            field=models.EmailField(
                blank=True, default="", max_length=255, verbose_name="Email"
            ),
        ),
    ]
