# Generated by Django 4.1 on 2022-08-17 14:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ppic", "0003_alter_productorder_product"),
    ]

    operations = [
        migrations.RenameField(
            model_name="deliverynotesubcont", old_name="product", new_name="supplier",
        ),
        migrations.RenameField(
            model_name="material", old_name="product", new_name="supplier",
        ),
    ]
