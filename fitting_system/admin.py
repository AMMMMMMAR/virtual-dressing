from django.contrib import admin
from .models import Size, Color, Product, ProductVariant, Inventory, BodyScan, Recommendation


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'chest_min', 'chest_max', 'waist_min', 'waist_max', 'height_min', 'height_max']
    search_fields = ['name']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code', 'category']
    list_filter = ['category']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'fit_type', 'gender', 'price', 'created_at']
    list_filter = ['category', 'fit_type', 'gender']
    search_fields = ['name', 'description']
    ordering = ['name']


class InventoryInline(admin.TabularInline):
    model = Inventory
    extra = 0
    fields = ['quantity', 'low_stock_threshold', 'last_updated']
    readonly_fields = ['last_updated']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'color', 'sku', 'get_stock_quantity', 'get_stock_status']
    list_filter = ['product__category', 'size', 'color']
    search_fields = ['product__name', 'sku']
    inlines = [InventoryInline]
    
    def get_stock_quantity(self, obj):
        try:
            return obj.inventory.quantity
        except Inventory.DoesNotExist:
            return 'N/A'
    get_stock_quantity.short_description = 'Stock'
    
    def get_stock_status(self, obj):
        try:
            inv = obj.inventory
            if inv.is_out_of_stock:
                return '🔴 Out of Stock'
            elif inv.is_low_stock:
                return '🟡 Low Stock'
            else:
                return '🟢 In Stock'
        except Inventory.DoesNotExist:
            return 'N/A'
    get_stock_status.short_description = 'Status'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product_variant', 'quantity', 'low_stock_threshold', 'get_status', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['product_variant__product__name', 'product_variant__sku']
    
    def get_status(self, obj):
        if obj.is_out_of_stock:
            return '🔴 Out of Stock'
        elif obj.is_low_stock:
            return '🟡 Low Stock'
        else:
            return '🟢 In Stock'
    get_status.short_description = 'Status'


@admin.register(BodyScan)
class BodyScanAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'height', 'chest', 'waist', 'shoulder_width', 'skin_tone', 'undertone', 'scanned_at']
    list_filter = ['skin_tone', 'undertone', 'scanned_at']
    search_fields = ['session_id']
    readonly_fields = ['session_id', 'scanned_at']
    ordering = ['-scanned_at']


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['body_scan', 'product', 'recommended_size', 'recommended_fit', 'priority', 'created_at']
    list_filter = ['recommended_size', 'recommended_fit', 'created_at']
    search_fields = ['body_scan__session_id', 'product__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at', '-priority']
