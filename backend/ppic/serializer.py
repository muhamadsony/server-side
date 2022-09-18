from rest_framework.serializers import ModelSerializer,StringRelatedField,ValidationError

from purchasing.models import Supplier
from django.db.models import Q,Prefetch
from math import ceil
from .models import *
from marketing.models import Customer
from manager.shortcuts import invalid

class DriverSerializer(ModelSerializer):
    class Meta:
        model = Driver
        fields = ['name']

class VehicleSerializer(ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['licence_part_number']


##################
#### Product Read Only Seriz
class WarehouseProductReadOnlySerializer(ModelSerializer):
    class Meta:
        model = WarehouseProduct
        fields = ['id','quantity','warehouse_type']
        depth = 1

class RequirementMaterialReadOnlySerializer(ModelSerializer):
    class Meta:
        model = RequirementMaterial
        fields = ['id','conversion','material']
        depth = 1

class RequirementProductReadOnlySerializer(ModelSerializer):
    class Meta:
        model = RequirementProduct
        fields = ['id','conversion','product']
        depth = 1

class ProcessReadOnlySerializer(ModelSerializer):
    warehouseproduct_set = WarehouseProductReadOnlySerializer(many=True)
    requirementproduct_set = RequirementProductReadOnlySerializer(many=True)
    requirementmaterial_set = RequirementMaterialReadOnlySerializer(many=True)

    class Meta:
        model = Process
        fields = ['id','process_name','order','process_type','warehouseproduct_set','requirementproduct_set','requirementmaterial_set']
        depth = 1

class ProductReadOnlySerializer(ModelSerializer):
    ppic_process_related = ProcessReadOnlySerializer(many=True)

    class Meta:
        model = Product
        fields = ['id','code','name','weight','image','process','price','ppic_process_related','type']
        depth = 1

class ProductCustomerReadOnlySerializer(ModelSerializer):
    ppic_product_related = ProductReadOnlySerializer(many=True)

    class Meta:
        model = Customer
        fields = ['id','name','email','phone','address','ppic_product_related']

#### Product read only seriz
######



#######
### product management seriz

class WarehouseProductManagementSerializer(ModelSerializer):
    class Meta:
        model = WarehouseProduct
        fields = '__all__'

class RequirementMaterialManagementSerializer(ModelSerializer):
    class Meta:
        model = RequirementMaterial
        exclude = ['process']

class RequirementProductManagementSerializer(ModelSerializer):
    class Meta:
        model = RequirementProduct
        exclude = ['process']

class RequirementProductManagement(ModelSerializer):
    
    def validate(self, attrs):
        product_in_process = attrs['process'].product

        product_needed = attrs['product']
        for process_of_product_needed in product_needed.ppic_process_related.all():
            if process_of_product_needed.requirementproduct_set.all().contains(product_in_process):
                raise ValidationError(f'{product_needed.name} tidak bisa menjadi kebutuhan pada semua proses {product_in_process.name}')

        return super().validate(attrs)

    class Meta:
        model = RequirementProduct
        fields = '__all__'

class RequirementMaterialManagement(ModelSerializer):
    class Meta:
        model = RequirementMaterial
        fields = '__all__'

class ProcessManagementSerializer(ModelSerializer):
    requirementproduct_set = RequirementProductManagementSerializer(many=True)
    requirementmaterial_set = RequirementMaterialManagementSerializer(many=True)
    class Meta:
        model = Process
        fields = ['id','process_name','process_type','requirementproduct_set','requirementmaterial_set']

class ProductManagementSerializer(ModelSerializer):
    ppic_process_related = ProcessManagementSerializer(many=True)

    def validate_ppic_process_related(self,attrs):
        len_attrs = len(attrs)
        if len_attrs == 0:
            invalid('Product setidaknya memiliki satu proses')
        
        requirementmaterial = attrs[0]['requirementmaterial_set']
        len_requirement_material = len(requirementmaterial)
        if len_requirement_material == 0:
            invalid('Proses pertama setidaknya memiliki satu kebutuhan material')
        
        return attrs
    
    def perform_delete(self, lst:list) -> None:
        for instance in lst:
            instance.delete()
    
    def perform_insert(self, lst:list, cls) -> None:
        cls.objects.bulk_create(lst)
    
    def perform_update(self, lst:list, cls, fields:list) -> None:
        cls.objects.bulk_update(lst,fields)

    def changed_material(self,obj:dict) -> None:
        self.perform_delete(obj['deleted'])
        self.perform_insert(obj['inserted'],obj['instance'])
        self.perform_update(obj['updated'],obj['instance'],['input','output','material','process'])
        
    def changed_product(self,obj:dict) -> None:
        self.perform_delete(obj['deleted'])
        self.perform_insert(obj['inserted'],obj['instance'])
        self.perform_update(obj['updated'],obj['instance'],['input','output','product','process'])
    
    def changed_warehouseproduct(self,obj:dict) -> None:
        self.perform_delete(obj['deleted'])
        self.perform_insert(obj['inserted'],obj['instance'])
        self.perform_update(obj['updated'],obj['instance'],['quantity','warehouse_type'])
    
    def changed_process(self,obj:dict) -> None:
        
        temp = 0
        for process in obj['deleted']:
            qty_wh = process.warehouseproduct_set.exclude(warehouse_type = 2).get().quantity
            temp += qty_wh
        
        last_wh = obj['updated'][-1].warehouseproduct_set.exclude(warehouse_type = 2 ).get() 
        last_wh.quantity += temp
        last_wh.save()
        
        ##### take all quantity deleted from warehouseproduct to updated warehouseproduct
        
        self.perform_delete(obj['deleted'])
        self.perform_update(obj['updated'],obj['instance'],['process_name','order','process_type'])

    def perform_changing(self,objs:dict) -> None:
        self.changed_product(objs['product'])
        self.changed_material(objs['material'])
        self.changed_warehouseproduct(objs['warehouseproduct'])
        self.changed_process(objs['process'])

    def update(self, instance, validated_data):
        '''
        update product -> process -> req material & req product & warehouse product
        '''
       
        changed_data = {
            'material': {
                'instance':RequirementMaterial,
                'deleted':[],
                'inserted':[],
                'updated':[]
            },
            'product': {
                'instance':RequirementProduct,
                'deleted':[],
                'inserted':[],
                'updated':[]
            },
            'warehouseproduct': {
                'instance':WarehouseProduct,
                'deleted':[],
                'inserted':[],
                'updated':[]
            },
            'process': {
                'instance':Process,
                'deleted':[],
                'updated':[]
            }
        }

        wh_type_subcont = WarehouseType.objects.get(id=2)
        wh_type_fg = WarehouseType.objects.get(id=1)

        many_process = validated_data.pop('ppic_process_related')
        len_process = len(many_process)

        instance_old_process = instance.ppic_process_related.all()
        len_instance_process = len(instance_old_process)

        instance.code = validated_data['code']
        instance.name = validated_data['name']
        instance.weight = validated_data['weight']
        instance.process = len_process
        instance.price = validated_data['price']
        instance.type = validated_data['type']
        instance.save() # perform update product
        order = 1

        for i in range(len_process):
            
            req_material = many_process[i].pop('requirementmaterial_set')
            len_material = len(req_material)

            req_product = many_process[i].pop('requirementproduct_set')
            len_product = len(req_product)
            
            if i > len_instance_process - 1:
                instance_process = Process.objects.create(**many_process[i],product=instance,order=order)
                new_process_type = instance_process.process_type.id
            else:
                instance_process = instance_old_process[i]
                old_process_type = instance_process.process_type.id

                instance_process.process_name = many_process[i]['process_name']
                instance_process.order = order
                instance_process.process_type = many_process[i]['process_type']
                # instance_process.save()
                changed_data['process']['updated'].append(instance_process)
                
                new_process_type = many_process[i]['process_type'].id

            instance_req_material = instance_process.requirementmaterial_set.all()
            len_instance_req_material = len(instance_req_material) - 1

            instance_req_product = instance_process.requirementproduct_set.all()
            len_instance_req_product = len(instance_req_product) - 1
            
            k = 0
            for k in range(len_material):
                if k > len_instance_req_material:
                    changed_data['material']['inserted'].append(RequirementMaterial(**req_material[k],process=instance_process))
                else:
                    instance_req_material[k].input = req_material[k].get('input',instance_req_material[k].input)
                    instance_req_material[k].output = req_material[k].get('output',instance_req_material[k].output)
                    instance_req_material[k].material = req_material[k]['material']
                    instance_req_material[k].process = instance_process                    
                    changed_data['material']['updated'].append(instance_req_material[k])

            changed_data['material']['deleted'] = changed_data['material']['deleted'][:] + instance_req_material[k+1:]
            
            j = 0
            for j in range(len_product):
                if j > len_instance_req_product:
                    changed_data['product']['inserted'].append(RequirementProduct(**req_product[j],process=instance_process))
                else:
                    instance_req_product[j].input = req_product[j].get('input',instance_req_product[j].input)
                    instance_req_product[j].output = req_product[j].get('output',instance_req_product[j].output)
                    instance_req_product[j].product = req_product[j]['product']
                    instance_req_product[j].process = instance_process                    
                    changed_data['product']['updated'].append(instance_req_product[j])

            changed_data['product']['deleted'] = changed_data['product']['deleted'][:] + instance_req_product[j+1:]

            wh_product = {
                'quantity':0,
                'process':instance_process,
                'product':instance,
            }

            wh_type_wip,created = WarehouseType.objects.get_or_create(id=order+2,name=f'Wip{order}')


            if i > len_instance_process - 1: # kalo prosesnya yang LAMA dah abis berarti insert
                if new_process_type == 2: # kalo proses itu SUBCONT
                        wh_product['warehouse_type'] = wh_type_subcont
                        changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
                
                if i == len_process - 1: # kalo proses barunya proses TERAKHIR
                    wh_product['warehouse_type'] = wh_type_fg
                    changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
                else: # kalo proses barunya bukan yang TERAKHIR
                    wh_product['warehouse_type'] = wh_type_wip
                    changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
            
            else: # asumsikan proses lama nya masih ada berarti update
                if i == len_process - 1: # proses barunya yang TERAKHIR
                    if i == len_instance_process - 1: # proses lama juga TERAKHIR
                        fg = instance_process.warehouseproduct_set.get(warehouse_type=1)
                        
                        if old_process_type == 2 and new_process_type != 2: # kalo proses lamanya itu subcont
                            subcont = instance_process.warehouseproduct_set.get(warehouse_type=2)
                            fg.quantity += subcont.quantity
                            changed_data['warehouseproduct']['deleted'].append(subcont)

                        elif old_process_type !=2 and new_process_type == 2:
                            wh_product['warehouse_type'] = wh_type_subcont
                            changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
                            
                        changed_data['warehouseproduct']['updated'].append(fg)

                    else: # proses lamanya BUKAN yang TERAKHIR
                        wip = instance_process.warehouseproduct_set.get(warehouse_type=order+2)
                        wip.warehouse_type = wh_type_fg
                        
                        if old_process_type == 2 and new_process_type != 2: # kalo proses lamanya itu subcont
                            subcont = instance_process.warehouseproduct_set.get(warehouse_type=2)
                            wip.quantity += subcont.quantity
                            changed_data['warehouseproduct']['deleted'].append(subcont)

                        elif old_process_type !=2 and new_process_type == 2:
                            wh_product['warehouse_type'] = wh_type_subcont
                            changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
                        
                        changed_data['warehouseproduct']['updated'].append(wip)
                
                else: # kalo proses baru BUKAN prosesnya yang TERAKHIR
                    if i == len_instance_process - 1: # prosesnya yang lama TERAKHIR
                        fg = instance_process.warehouseproduct_set.get(warehouse_type=1)
                        fg.warehouse_type = wh_type_wip

                        if old_process_type == 2 and new_process_type != 2: # kalo proses lamanya itu subcont
                            subcont = instance_process.warehouseproduct_set.get(warehouse_type=2)
                            fg.quantity += subcont.quantity
                            changed_data['warehouseproduct']['deleted'].append(subcont)    
                            
                        elif old_process_type !=2 and new_process_type == 2:
                            wh_product['warehouse_type'] = wh_type_subcont
                            changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
                            
                        changed_data['warehouseproduct']['updated'].append(fg)

                    else: #proses lama juga BUKAN yang TERAKHIR
                        
                        wip = instance_process.warehouseproduct_set.get(warehouse_type=order+2)

                        if old_process_type == 2 and new_process_type != 2: # kalo proses lamanya itu subcont
                            subcont = instance_process.warehouseproduct_set.get(warehouse_type=2)
                            wip.quantity += subcont.quantity
                            changed_data['warehouseproduct']['deleted'].append(subcont)

                        elif old_process_type !=2 and new_process_type == 2:
                            wh_product['warehouse_type'] = wh_type_subcont
                            changed_data['warehouseproduct']['inserted'].append(WarehouseProduct(**wh_product))
                            
                        changed_data['warehouseproduct']['updated'].append(wip)

            order += 1

        changed_data['process']['deleted'] = changed_data['process']['deleted'][:] + instance_old_process[i+1:]


        self.perform_changing(changed_data)

        return instance

    def create(self, validated_data):
        '''
        create product -> process -> requirement material & requirement product & warehouse product
        '''
        many_process = validated_data.pop('ppic_process_related')
        len_process = len(many_process)

        req_material_bulk = []
        req_product_bulk = []
        whproduct_bulk = []
        order = 1

        instance_product = Product.objects.create(**validated_data,process=len_process)
        wh_type_subcont = WarehouseType.objects.get(id=2)

        for each_process in many_process:
            many_req_material = each_process.pop('requirementmaterial_set')
            many_req_product = each_process.pop('requirementproduct_set')
            instance_process = Process.objects.create(**each_process,product=instance_product,order=order)
            process_type = instance_process.process_type.name

            for req_material in many_req_material:
                req_material_bulk.append(RequirementMaterial(**req_material,process=instance_process))
            for req_product in many_req_product:
                req_product_bulk.append(RequirementProduct(**req_product,process=instance_process))
            
            wh_wip_type,created = WarehouseType.objects.get_or_create(id=order+2,name=f'Wip{order}')
            
            wh_product = {
                'quantity':0,
                'process':instance_process,
                'product':instance_product,
                'warehouse_type':wh_wip_type,
            }

            if process_type == 'subcont' or process_type == 'Subcont':
                whproduct_bulk.append(WarehouseProduct(**wh_product))

                wh_product['warehouse_type'] = wh_type_subcont
                whproduct_bulk.append(WarehouseProduct(**wh_product))
            else:
                whproduct_bulk.append(WarehouseProduct(**wh_product))

            order += 1

        RequirementMaterial.objects.bulk_create(req_material_bulk)
        RequirementProduct.objects.bulk_create(req_product_bulk)
        WarehouseProduct.objects.bulk_create(whproduct_bulk)

        return instance_product

    class Meta:
        model = Product
        exclude = ['process']


### Product management seriz
######

#########
##### material read only seriz

class RequirementReadOnlySerializer(RequirementMaterialReadOnlySerializer):

    class Meta(RequirementMaterialReadOnlySerializer.Meta):
        fields = ['id','input','process','output']
        depth = 2

class WarehouseMaterialReadOnlySerializer(ModelSerializer):
    class Meta:
        model = WarehouseMaterial
        fields = ['id','quantity']

class MaterialReadOnlySerializer(ModelSerializer):
    ppic_requirementmaterial_related = RequirementReadOnlySerializer(many=True)
    warehousematerial = WarehouseMaterialReadOnlySerializer()
    class Meta:
        model = Material
        exclude = ['supplier']
        depth = 1

class MaterialSupplierReadOnlySerializer(ModelSerializer):
    ppic_material_related = MaterialReadOnlySerializer(many=True)
    class Meta:
        model = Supplier
        fields = '__all__'

#### material read only seriz
#########



###### Serializers for product







####### Serializers for material


class MaterialSerializer(ModelSerializer):

    def create(self, validated_data):
        instance = super().create(validated_data)
        WarehouseMaterial.objects.create(quantity=0,material=instance)
        return instance 
    
    def update(self, instance, validated_data):
        req_material = instance.ppic_requirementmaterial_related.all()
        wh_material = instance.warehousematerial

        if len(req_material) > 0:
            raise ValidationError('Tidak bisa mengubah data material yang menjadi kebutuhan produksi')
        if wh_material.quantity > 0:
            raise ValidationError('Tidak bisa mengubah data material yang memiliki stok di gudang')
        
        return super().update(instance, validated_data)
    
    class Meta:
        model = Material
        fields = ['id','name','spec','length','width','thickness','uom','supplier','weight','image']

class ConversionUomReadOnlySerializer(ModelSerializer):
    class Meta:
        model = ConversionUom
        fields = '__all__'
        depth = 1

class ConversionUomManagementSerializer(ModelSerializer):

    def validate(self, attrs):
        input = attrs['uom_input']
        output = attrs['uom_output']

        if input == output:
            raise ValidationError('Tidak bisa memasukkan data konversi dari unit yang sama')

        uoms = ConversionUom.objects.filter(Q(uom_input = output) & Q(uom_output = input)).first()
        
        if uoms is None:
            return super().validate(attrs)
        raise ValidationError(f'{input.name} sudah menjadi dasar konversi dari {output.name}')

    class Meta:
        model = ConversionUom
        fields = '__all__'

class BasedConversionReadOnlySerializer(ModelSerializer):
    class Meta:
        model = BasedConversionMaterial
        fields = '__all__'
        depth = 2

class BasedConversionManagementSerializer(ModelSerializer):

    def validate(self, attrs):
        input = attrs['material_input']
        unit_input  = input.uom
        output = attrs['material_output']
        unit_output = output.uom
        

        uoms = ConversionUom.objects.filter(Q(uom_input = unit_input) & Q(uom_output = unit_output)).first()

        if uoms is None:
            raise ValidationError('Tidak ada data konversi unit pada material tersebut')
        if input == output:
            raise ValidationError('Tidak bisa mengkonversi material yang sama')

        return super().validate(attrs)

    class Meta:
        model = BasedConversionMaterial
        fields = '__all__'

class ConversionMaterialReportReadOnlySerializer(ModelSerializer):
    class Meta:
        model = ConversionMaterialReport
        fields = '__all__'
        depth = 2

class ConversionMaterialReportManagementSerializer(ModelSerializer):
    
    def validate(self, attrs):
        '''
        validasi untuk kecukupan material
        '''
        input = attrs['material_input']
        output = attrs['material_output']
        uoms = BasedConversionMaterial.objects.filter(Q(material_input = input) & Q(material_output = output)).first()
        if uoms is None:
            raise ValidationError('Tidak ada data konversi pada kedua material tersebut')
        
        used_material = (attrs['quantity_output'] / uoms.quantity_output) * uoms.quantity_input
        stok = input.warehousematerial.quantity
        if used_material > stok:
            raise ValidationError(f'Stok material {input.name} tidak cukup')
        
        return super().validate(attrs)
    
    def create(self, validated_data):
        input = validated_data['material_input']
        output = validated_data['material_output']

        uoms = BasedConversionMaterial.objects.get(material_input = input, material_output=output)
        used_material = (validated_data['quantity_output'] / uoms.quantity_output) * uoms.quantity_input
        
        rest_material = ceil(used_material) - used_material

        if rest_material > 0:
            wh_scrap = WarehouseScrapMaterial.objects.filter(material=input).first()
            if wh_scrap is None:
                WarehouseScrapMaterial.objects.create(quantity = rest_material, material = input)
            else:
                wh_scrap.quantity += rest_material
                wh_scrap.save()
        
        wh_material_input = input.warehousematerial
        wh_material_input.quantity -= ceil(used_material)
        wh_material_input.save()

        wh_material_output = output.warehousematerial
        wh_material_output.quantity += validated_data['quantity_output']
        wh_material_output.save()

        validated_data['quantity_input'] = ceil(used_material)

        return super().create(validated_data)

    class Meta:
        model = ConversionMaterialReport
        fields = '__all__'
        read_only_fields = ['quantity_input']

class DetailMrpReadOnlySerializer(ModelSerializer):

    class Meta:
        model = DetailMrp
        fields = ['id','product','quantity','quantity_production']
        depth = 1

class MrpReadOnlySerializer(ModelSerializer):
    detailmrp_set = DetailMrpReadOnlySerializer(many=True)

    class Meta:
        model = MaterialRequirementPlanning
        fields = ['id','material','quantity','detailmrp_set']
        depth = 2

class DetailMrpManagementSerializer(ModelSerializer):
    class Meta:
        model = DetailMrp
        fields = ['id','product','quantity','quantity_production']

class MrpManagementSerializer(ModelSerializer):
    detailmrp_set = DetailMrpManagementSerializer(many=True)

    def validate_detailmrp_set(self,attrs):
        quantity_req = self.initial_data['quantity']
        temp = 0
        for detailmrp in attrs:
            temp += detailmrp['quantity']
        if temp > quantity_req:
            raise ValidationError('Jumlah kebutuhan berlebih dari jumlah permintaan')

        return attrs
    
    def update(self, instance, validated_data):
        detailmrps = validated_data.pop('detailmrp_set')
        len_detailmrps = len(detailmrps)

        instance_detailmrps = instance.detailmrp_set.all()
        len_instance_mrps = len(instance_detailmrps)

        instance.quantity = validated_data['quantity']
        instance.material = validated_data['material']
        instance.save()

        for i in range(len_detailmrps):
            if i > len_instance_mrps - 1:
                DetailMrp.objects.create(**detailmrps[i],mrp=instance)
            else:
                instance_detailmrps[i].quantity = detailmrps[i]['quantity']
                instance_detailmrps[i].quantity_production = detailmrps[i]['quantity_production']
                instance_detailmrps[i].product = detailmrps[i]['product']
                instance_detailmrps[i].save()

        return instance

    def create(self, validated_data):
        detailmrps = validated_data.pop('detailmrp_set')
        instance = super().create(validated_data)
        
        for detailmrp in detailmrps:
            DetailMrp.objects.create(**detailmrp,mrp=instance)

        return instance

    class Meta:
        model = MaterialRequirementPlanning
        fields = ['id','quantity','material','detailmrp_set']

class WarehouseMaterialManagementSerializer(ModelSerializer):
    class Meta:
        model = WarehouseMaterial
        fields = '__all__'
        read_only_fields = ['id','material']

class WarehouseMaterialReadOnlySerializer(ModelSerializer):
    class Meta:
        model = WarehouseMaterial
        exclude = ['material']

class WarehouseScrapReadOnlySerializer(ModelSerializer):
    class Meta:
        model = WarehouseScrapMaterial
        fields = ['id','material','quantity']
        depth = 2

class WarehouseScrapManagementSerializer(ModelSerializer):
    class Meta:
        model = WarehouseScrapMaterial
        fields = '__all__'

class MaterialUomReadOnlySerializer(ModelSerializer):
    warehousematerial = WarehouseMaterialReadOnlySerializer()
    class Meta:
        model = Material
        exclude = ['uom']
        depth = 1

class UomWarehouseMaterialSerializer(ModelSerializer):
    material_set = MaterialUomReadOnlySerializer(many=True)
    class Meta:
        model = UnitOfMaterial
        fields = '__all__'

class UomManagementSerializer(ModelSerializer):
    class Meta:
        model = UnitOfMaterial
        fields = '__all__'


class StockWarehouseProductReadOnlySerializer(ModelSerializer):
    class Meta:
        model = WarehouseProduct
        exclude = ['warehouse_type']
        depth = 1

class WarehouseProductManagementSerializer(ModelSerializer):
    '''
    serializer for update stock product eg: wip,subcont,finishgood
    '''
    class Meta:
        model = WarehouseProduct
        fields = '__all__'
        read_only_fields = ['process','product','warehouse_type']

class WarehouseTypeReadOnlySerializer(ModelSerializer):
    warehouseproduct_set = StockWarehouseProductReadOnlySerializer(many=True)
    class Meta:
        model = WarehouseType
        fields = ['id','name','warehouseproduct_set']


class MaterialReceiptReadOnlySerializer(ModelSerializer):
    class Meta:
        model = MaterialReceipt
        exclude = ['delivery_note_material']
        depth = 2

class DeliveryNoteMaterialReadOnlySerializer(ModelSerializer):
    materialreceipt_set = MaterialReceiptReadOnlySerializer(many=True)
    class Meta:
        model = DeliveryNoteMaterial
        fields = ['id','code','created','note','materialreceipt_set']

class SupplierDeliveryNoteReadOnlySerializer(ModelSerializer):
    ppic_deliverynotematerial_related = DeliveryNoteMaterialReadOnlySerializer(many=True)
    class Meta:
        model = Supplier
        fields = '__all__'

class MaterialReceiptManagementSerializer(ModelSerializer):
    
    def validate_material_order(self,attrs):
        if attrs.done:
                raise ValidationError('Order tersebut sudah selesai')
        return attrs
    
    def create(self, validated_data):
        material_order = validated_data['material_order']
        material_order.arrived += validated_data['quantity']
        whmaterial = material_order.material.warehousematerial
        whmaterial.quantity += validated_data['quantity']
        
        if material_order.arrived >= material_order.ordered:
            material_order.done = True
        
        whmaterial.save()
        material_order.save()

        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance_mo = instance.material_order
        instance_wh = instance_mo.material.warehousematerial

        instance_mo.arrived -= instance.quantity
        instance_wh.quantity -= instance.quantity
        
        if instance_wh.quantity < 0:
            raise ValidationError('Edit data gagal, karena material sudah digunakan untuk produksi')
        
        instance_mo.arrived += validated_data['quantity']
        instance_wh.quantity += validated_data['quantity']
        
        if instance_mo.arrived >=instance_mo.ordered:
            instance_mo.done = True
        else:
            instance_mo.done = False

        instance_mo.save()
        instance_wh.save()

        return super().update(instance, validated_data)

    class Meta:
        model = MaterialReceipt
        fields = '__all__'

class DeliveryNoteMaterialManagementSerializer(ModelSerializer):

    class Meta:
        model = DeliveryNoteMaterial
        fields = '__all__'


class ProductDeliverCustomerReadOnlySerializer(ModelSerializer):
    '''
    seriz for get data product delivery depth to 2 relations below
    '''
    class Meta:
        model = ProductDeliverCustomer
        exclude = ['delivery_note_customer']
        depth = 2

class DeliveryNoteCustomerReadOnlySerializer(ModelSerializer):
    '''
    seriz for get data delivery note
    '''
    productdelivercustomer_set = ProductDeliverCustomerReadOnlySerializer(many=True)
    class Meta:
        model = DeliveryNoteCustomer
        exclude = ['customer']

class CustomerDeliveryNoteReadOnlySerializer(ModelSerializer):
    '''
    seriz for read data from customer -> delivery note -> product delivery
    '''
    ppic_deliverynotecustomer_related = DeliveryNoteCustomerReadOnlySerializer(many=True)
    class Meta:
        model = Customer
        fields = '__all__'

class DeliveryNoteCustomerManagementSerializer(ModelSerializer):
    '''
    seriz for management delivery note customer
    '''
    class Meta:
        model = DeliveryNoteCustomer
        fields = '__all__'

class ProductDeliverCustomerManagementSerializer(ModelSerializer):
    '''
    seriz for management product delivery
    '''    
    def validate_product_order(self,attrs):
        if attrs.done:
            raise ValidationError('Order tersebut sudah selesai')

        return attrs
    
    def validate(self, attrs):
        po = attrs['product_order']
        available_quantity_deliver = po.ordered - po.delivered
        wh_product = po.product.ppic_warehouseproduct_related.get(warehouse_type=1)

        if attrs['quantity'] > available_quantity_deliver:
            raise ValidationError('Jumlah pengiriman melebihi jumlah order')
        
        if attrs['quantity'] > wh_product.quantity:
            raise ValidationError('Stock finish good tidak cukup')

        return super().validate(attrs)

    def fluence_stock(self,po,wh_product,quantity):

        wh_product.quantity -= quantity
        po.delivered += quantity

        if po.delivered >= po.ordered:
            po.done = True
        else:
            po.done = False

        po.save()
        wh_product.save()

    def fluence_stock_update(self,po,wh_product,old_quantity,new_quantity):
        
        wh_product.quantity += old_quantity
        po.delivered -= old_quantity

        self.fluence_stock(po,wh_product,new_quantity)

    def update(self, instance, validated_data):
        if instance.paid:
            raise ValidationError('Pengiriman product sudah lunas')
        wh_product = instance.product_order.product.ppic_warehouseproduct_related.get(warehouse_type=1)
        
        self.fluence_stock_update(instance.product_order,wh_product,instance.quantity,validated_data['quantity'])
        
        return super().update(instance, validated_data)

    def create(self, validated_data):
        po = validated_data['product_order']
        wh_product = po.product.ppic_warehouseproduct_related.get(warehouse_type=1)
        self.fluence_stock(po,wh_product,validated_data['quantity'])

        return super().create(validated_data)

    class Meta:
        model = ProductDeliverCustomer
        fields = '__all__'


class MaterialProductionReportReadOnlySerializer(ModelSerializer):
    class Meta:
        model = MaterialProductionReport
        exclude = ['production_report']
        depth = 1

class ProductProductionReportReadOnlySerializer(ModelSerializer):
    class Meta:
        model = ProductProductionReport
        exclude = ['production_report']
        depth = 1

class ProductionReportReadOnlySerializer(ModelSerializer):
    productproductionreport_set = ProductProductionReportReadOnlySerializer(many=True)
    materialproductionreport_set = MaterialProductionReportReadOnlySerializer(many=True)

    class Meta:
        model = ProductionReport
        fields = '__all__'
        depth = 1        



class ProductionReportManagementSerializer(ModelSerializer):


    def suffciency_req_material_check(self,req_materials,production_quantity:int):
        
        for req_material in req_materials:
            wh_material = req_material.material.warehousematerial
            stock_in_wh = wh_material.quantity
            used_material = ceil((production_quantity / req_material.output) * req_material.input)
            if used_material > stock_in_wh:
                raise ValidationError(f'Jumlah stok {req_material.material.name} tidak cukup')
 

    def sufficiency_req_product_check(self,req_products,production_quantity:int):
        
        for req_product in req_products:
            product = req_product.product
            wh_product = product.ppic_warehouseproduct_related.first()
            stock_in_whproduct = wh_product.quantity
            used_product = (production_quantity/req_product.output) * req_product.input
            if used_product > stock_in_whproduct:
                raise ValidationError(f'Jumlah stok produk {product.name} tidak cukup')

    def validate(self, attrs):

        product = attrs['product']
        process = attrs['process']
        process_type = process.process_type
        order = process.order
        quantity_production = attrs['quantity'] + attrs['quantity_not_good']

        if order > 1 and process_type.id !=2:
            prev_process = Process.objects.get(order = order-1, product = product)
            warehouse_wip = prev_process.warehouseproduct_set.filter(warehouse_type__gt = 2).first()
            
            if quantity_production > warehouse_wip.quantity:
                raise ValidationError(f'Jumlah stok wip {product.name} kurang')

        if process_type.id == 2:
            warehouse_subcont = process.warehouseproduct_set.filter(warehouse_type =2).first()
            if quantity_production > warehouse_subcont.quantity:
                raise ValidationError(f'Jumlah produksi yang anda input berlebih')

        if process not in product.ppic_process_related.all():
            raise ValidationError(f'Proses tersebut bukan bagian dari work in process product {product.name}')

        req_product = process.requirementproduct_set.select_related('product').prefetch_related(
            Prefetch('product__ppic_warehouseproduct_related',queryset = WarehouseProduct.objects.filter(warehouse_type = 1)))
        
        req_material = process.requirementmaterial_set.select_related('material__warehousematerial')
        
        self.suffciency_req_material_check(req_material,quantity_production)
        self.sufficiency_req_product_check(req_product,quantity_production)

        return super().validate(attrs)


    def create(self, validated_data):

        product = validated_data['product']
        process = validated_data['process']
        process_type = process.process_type
        quantity_production = validated_data['quantity'] + validated_data['quantity_not_good']
        order = process.order
        
        inserted = {
            'material_report':[],
            'product_report':[]
        }

        updated = {
            'wh_material':[],
            'wh_product':[]
        }

        production_report = super().create(validated_data)

        if order > 1 and process_type.id !=2:

            prev_process = Process.objects.filter(order = order-1,product=product).prefetch_related(
                Prefetch('warehouseproduct_set',queryset=WarehouseProduct.objects.filter(warehouse_type__gt=2))).get()

            warehouse_wip = prev_process.warehouseproduct_set.first()
            warehouse_wip.quantity -= (quantity_production)
            warehouse_wip.save()
        
        if process_type.id == 2:
            warehouse_subcont = process.warehouseproduct_set.filter(warehouse_type = 2).first()
            warehouse_subcont.quantity -= (quantity_production)
            warehouse_subcont.save()
        
        req_materials = process.requirementmaterial_set.select_related('material__warehousematerial')
        req_products = process.requirementproduct_set.select_related('product').prefetch_related(
            Prefetch('product__ppic_warehouseproduct_related',queryset = WarehouseProduct.objects.filter(warehouse_type = 1)))

        for req_material in req_materials:
            material = req_material.material
            wh_material = material.warehousematerial
            used_material = (quantity_production / req_material.output) * req_material.input
            rest_material = ceil(used_material) - used_material
            
            if rest_material > 0:

                obj,created = WarehouseScrapMaterial.objects.get_or_create(material=material)
                obj.quantity += rest_material
                obj.save()

            wh_material.quantity -= ceil(used_material)
            updated['wh_material'].append(wh_material)
            inserted['material_report'].append(MaterialProductionReport(quantity=used_material,material=material,production_report=production_report))

        for req_product in req_products:
            product = req_product.product
            wh_product = product.ppic_warehouseproduct_related.first()
            used_product = ceil((quantity_production / req_product.output) * req_product.input)

            wh_product.quantity -= used_product

            updated['wh_product'].append(wh_product)
            inserted['product_report'].append(ProductProductionReport(quantity=used_product,product=product,production_report=production_report))

        wh_current_wip = process.warehouseproduct_set.exclude(warehouse_type = 2).first()
        wh_current_wip.quantity += validated_data['quantity']

        updated['wh_product'].append(wh_current_wip)

        WarehouseProduct.objects.bulk_update(updated['wh_product'],['quantity'])
        WarehouseMaterial.objects.bulk_update(updated['wh_material'],['quantity'])

        MaterialProductionReport.objects.bulk_create(inserted['material_report'])
        ProductProductionReport.objects.bulk_create(inserted['product_report'])

        return production_report
    
    def invalid_requirement(self):

        return invalid('Tidak bisa mengubah laporan produksi')

    def requirement_check(self,instance):
        process = instance.process

        material_reports = instance.materialproductionreport_set.select_related('material')
        product_reports = instance.productproductionreport_set.select_related('product')

        req_materials = process.requirementmaterial_set.select_related('material__warehousematerial')
        req_products = process.requirementproduct_set.select_related('product').prefetch_related(
            Prefetch('product__ppic_warehouseproduct_related',queryset = WarehouseProduct.objects.filter(warehouse_type = 1)))
        
        req_mats = [x.material for x in req_materials]
        req_prod = [x.product for x in req_products]


        for report in material_reports:
            try:
                req_mats.remove(report.material)
            except:
                self.invalid_requirement()

        for report in product_reports:
            try:
                req_prod.remove(report.product)
            except:
                self.invalid_requirement()

        if len(req_mats) > 0:
            self.invalid_requirement()
        if len(req_prod) > 0:
            self.invalid_requirement()

        return req_materials,req_products,material_reports,product_reports

    def update(self, instance, validated_data):

        prev_quantity_production = instance.quantity + instance.quantity_not_good
        quantity_production = validated_data['quantity'] + validated_data['quantity_not_good']
        
        instance_product = instance.product
        process = instance.process

        req_materials,req_products,material_reports,product_reports = self.requirement_check(instance)

        process_type = process.process_type
        
        order = process.order

        updated = {
            'wh_material':[],
            'wh_product':[],
            'material_reports':[],
            'product_reports':[],
        }

        production_report = super().update(instance, validated_data)

        if order > 1 and process_type.id !=2:
            prev_process = Process.objects.filter(order = order-1,product=instance_product).prefetch_related(
                Prefetch('warehouseproduct_set',queryset=WarehouseProduct.objects.filter(warehouse_type__gt=2))).get()

            warehouse_wip = prev_process.warehouseproduct_set.first()
            warehouse_wip.quantity += (prev_quantity_production)
            warehouse_wip.quantity -= (quantity_production)
            warehouse_wip.save()
        
        if process_type.id == 2:
            warehouse_subcont = process.warehouseproduct_set.filter(warehouse_type = 2).first()
            warehouse_subcont.quantity += (prev_quantity_production)
            warehouse_subcont.quantity -= (quantity_production)    
            warehouse_subcont.save()
        
        for req_material in req_materials:
            material = req_material.material
            wh_material = material.warehousematerial
            prev_used_material = (prev_quantity_production / req_material.output) * req_material.input
            ceiled_prev_used_material = ceil(prev_used_material)
            prev_rest_material = ceiled_prev_used_material - prev_used_material

            current_used_material = (quantity_production / req_material.output) * req_material.input
            ceiled_current_used_material = ceil(current_used_material)
            current_rest_material = ceiled_current_used_material - current_used_material


            wh_material.quantity += ceiled_prev_used_material
            wh_material.quantity -= ceiled_current_used_material
            
            try:
                obj = WarehouseScrapMaterial.objects.get(material=material)
            except:
                obj = WarehouseScrapMaterial.objects.create(material=material,quantity=0)

            if current_rest_material > 0:
                if prev_rest_material > 0:
                    obj.quantity -= prev_rest_material
                    obj.quantity += current_rest_material
                else:
                    obj.quantity += current_rest_material
            else:
                if prev_rest_material > 0:
                    obj.quantity -= prev_rest_material
            obj.save()

            
            updated['wh_material'].append(wh_material)

            for report in material_reports.filter(material=material):
                report.quantity = ceiled_current_used_material
                updated['material_reports'].append(report)
                

        for req_product in req_products:
            product = req_product.product
            wh_product = product.ppic_warehouseproduct_related.first()
            prev_used_product = ceil((prev_quantity_production / req_product.output) * req_product.input)
            used_product = ceil((quantity_production / req_product.output) * req_product.input)

            wh_product.quantity += prev_used_product
            wh_product.quantity -= used_product

            updated['wh_product'].append(wh_product)

            for report in product_reports.filter(product=product):
                report.quantity = used_product
                updated['product_reports'].append(report)
                


        wh_current_wip = process.warehouseproduct_set.exclude(warehouse_type = 2).first()
        wh_current_wip.quantity -= instance.quantity
        wh_current_wip.quantity += validated_data['quantity']
        
        updated['wh_product'].append(wh_current_wip)

        WarehouseProduct.objects.bulk_update(updated['wh_product'],['quantity'])
        WarehouseMaterial.objects.bulk_update(updated['wh_material'],['quantity'])

        MaterialProductionReport.objects.bulk_update(updated['material_reports'],['quantity'])
        ProductProductionReport.objects.bulk_update(updated['product_reports'],['quantity'])

        return production_report
    



    class Meta:
        model = ProductionReport
        fields = '__all__'

















