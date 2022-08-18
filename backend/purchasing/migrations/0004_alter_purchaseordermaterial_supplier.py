# Generated by Django 4.1 on 2022-08-17 15:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("purchasing", "0003_rename_product_purchaseordermaterial_supplier"),
    ]

    operations = [
        migrations.AlterField(
            model_name="purchaseordermaterial",
            name="supplier",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(app_label)s_%(class)s_related",
                related_query_name="%(app_label)s_%(class)ss",
                to="purchasing.supplier",
            ),
        ),
    ]
