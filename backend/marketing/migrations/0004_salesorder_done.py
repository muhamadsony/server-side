# Generated by Django 4.1 on 2022-08-22 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0003_salesorder_created"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesorder",
            name="done",
            field=models.BooleanField(default=False),
        ),
    ]