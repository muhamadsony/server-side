# Generated by Django 4.1 on 2022-12-22 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0009_invoice_closed_invoice_done_salesorder_closed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="salesorder",
            name="description",
            field=models.TextField(default=""),
        ),
    ]