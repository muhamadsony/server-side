# Generated by Django 4.1 on 2022-08-19 09:39

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("ppic", "0006_detailmrp"),
    ]

    operations = [
        migrations.CreateModel(
            name="Machine",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
            ],
            options={"abstract": False,},
        ),
        migrations.CreateModel(
            name="Operator",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
            ],
            options={"abstract": False,},
        ),
        migrations.RenameField(
            model_name="processtype", old_name="type_name", new_name="name",
        ),
        migrations.RenameField(
            model_name="producttype", old_name="type_name", new_name="name",
        ),
        migrations.RenameField(
            model_name="unitofmaterial", old_name="type_name", new_name="name",
        ),
        migrations.RenameField(
            model_name="warehousetype", old_name="type_name", new_name="name",
        ),
        migrations.CreateModel(
            name="ProductionReport",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveBigIntegerField()),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("quantity_not_good", models.PositiveBigIntegerField()),
                (
                    "machine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="ppic.machine"
                    ),
                ),
                (
                    "operator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="ppic.operator"
                    ),
                ),
                (
                    "process",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="ppic.process"
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_related",
                        related_query_name="%(app_label)s_%(class)ss",
                        to="ppic.product",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
        migrations.CreateModel(
            name="MaterialProductionReport",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveBigIntegerField()),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_related",
                        related_query_name="%(app_label)s_%(class)ss",
                        to="ppic.material",
                    ),
                ),
                (
                    "production_report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ppic.productionreport",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
    ]
