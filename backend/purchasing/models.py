from django.db import models
from manager.models import AbstractCustomerVendor,AbstractCode,AbstractCreated

# Create your models here.

class Supplier(AbstractCustomerVendor):
    pass

class AbstractSupplier(models.Model):
    supplier = models.ForeignKey(Supplier,on_delete=models.CASCADE,related_name="%(app_label)s_%(class)s_related",related_query_name="%(app_label)s_%(class)ss",null=True)

    class Meta:
        abstract = True

class PurchaseOrderMaterial(AbstractCode,AbstractSupplier,AbstractCreated):
    done = models.BooleanField(default=False)

    class Meta(AbstractCode.Meta,AbstractSupplier.Meta,AbstractCreated.Meta):
        pass
    



















