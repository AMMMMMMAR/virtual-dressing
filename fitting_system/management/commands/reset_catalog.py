"""
reset_catalog.py — management command
Wipes all Product/ProductVariant/Inventory data and seeds exactly
4 products with realistic inventory stock distribution.
"""
from django.core.management.base import BaseCommand
from fitting_system.models import Product, ProductVariant, Inventory, Color, Size

# Using actual color names from the DB:
# Black, White, Navy, Ash Grey, Cream, Burgundy, Sky Blue, Blush Pink

CATALOG = [
    {
        'name': 'Classic Cotton Shirt',
        'category': 'shirt',
        'gender': 'men',
        'price': '49.99',
        'description': (
            'A timeless classic cotton shirt perfect for any occasion. '
            'Made from 100% premium cotton for maximum comfort and breathability.'
        ),
        'stock': [
            # size,    color,          qty
            ('S',  'Black',      45),
            ('S',  'White',      50),
            ('S',  'Navy',       30),
            ('S',  'Ash Grey',   20),
            ('S',  'Cream',       4),   # low
            ('S',  'Burgundy',    0),   # OOS
            ('S',  'Sky Blue',   22),
            ('S',  'Blush Pink',  0),   # OOS
            ('M',  'Black',      50),
            ('M',  'White',      50),
            ('M',  'Navy',       35),
            ('M',  'Ash Grey',   28),
            ('M',  'Cream',      15),
            ('M',  'Burgundy',    3),   # low
            ('M',  'Sky Blue',   40),
            ('M',  'Blush Pink',  0),   # OOS
            ('L',  'Black',      38),
            ('L',  'White',      42),
            ('L',  'Navy',       18),
            ('L',  'Ash Grey',   10),
            ('L',  'Cream',       2),   # low
            ('L',  'Burgundy',    0),   # OOS
            ('L',  'Sky Blue',   25),
            ('L',  'Blush Pink',  0),   # OOS
            ('XL', 'Black',      20),
            ('XL', 'White',      15),
            ('XL', 'Navy',        4),   # low
            ('XL', 'Ash Grey',    0),   # OOS
            ('XL', 'Cream',       0),   # OOS
            ('XL', 'Burgundy',    0),   # OOS
            ('XL', 'Sky Blue',    8),
            ('XL', 'Blush Pink',  0),   # OOS
        ],
    },
    {
        'name': 'Casual Denim Jeans',
        'category': 'pants',
        'gender': 'men',
        'price': '79.99',
        'description': (
            'Comfortable denim jeans with a classic fit. Durable and stylish '
            'for everyday wear with premium denim fabric.'
        ),
        'stock': [
            ('S',  'Black',      30),
            ('S',  'White',       0),   # OOS
            ('S',  'Navy',       25),
            ('S',  'Ash Grey',   12),
            ('S',  'Cream',       0),   # OOS
            ('S',  'Burgundy',    0),   # OOS
            ('S',  'Sky Blue',   40),
            ('S',  'Blush Pink',  0),   # OOS
            ('M',  'Black',      45),
            ('M',  'White',       0),   # OOS
            ('M',  'Navy',       38),
            ('M',  'Ash Grey',   20),
            ('M',  'Cream',       0),   # OOS
            ('M',  'Burgundy',    0),   # OOS
            ('M',  'Sky Blue',   50),
            ('M',  'Blush Pink',  0),   # OOS
            ('L',  'Black',      35),
            ('L',  'White',       0),   # OOS
            ('L',  'Navy',       22),
            ('L',  'Ash Grey',    5),   # low
            ('L',  'Cream',       0),   # OOS
            ('L',  'Burgundy',    0),   # OOS
            ('L',  'Sky Blue',   28),
            ('L',  'Blush Pink',  0),   # OOS
            ('XL', 'Black',      18),
            ('XL', 'White',       0),   # OOS
            ('XL', 'Navy',        3),   # low
            ('XL', 'Ash Grey',    0),   # OOS
            ('XL', 'Cream',       0),   # OOS
            ('XL', 'Burgundy',    0),   # OOS
            ('XL', 'Sky Blue',   10),
            ('XL', 'Blush Pink',  0),   # OOS
        ],
    },
    {
        'name': 'Oversized Blouse',
        'category': 'shirt',
        'gender': 'women',
        'price': '54.99',
        'description': (
            'Relaxed oversized blouse with an elegant drape. Perfect for '
            'casual or smart-casual occasions with lightweight breathable fabric.'
        ),
        'stock': [
            ('S',  'Black',      35),
            ('S',  'White',      40),
            ('S',  'Navy',        0),   # OOS
            ('S',  'Ash Grey',    8),
            ('S',  'Cream',      30),
            ('S',  'Burgundy',   12),
            ('S',  'Sky Blue',    4),   # low
            ('S',  'Blush Pink', 45),
            ('M',  'Black',      40),
            ('M',  'White',      50),
            ('M',  'Navy',        0),   # OOS
            ('M',  'Ash Grey',   15),
            ('M',  'Cream',      35),
            ('M',  'Burgundy',   20),
            ('M',  'Sky Blue',    2),   # low
            ('M',  'Blush Pink', 48),
            ('L',  'Black',      28),
            ('L',  'White',      32),
            ('L',  'Navy',        0),   # OOS
            ('L',  'Ash Grey',    3),   # low
            ('L',  'Cream',      18),
            ('L',  'Burgundy',    5),   # low
            ('L',  'Sky Blue',    0),   # OOS
            ('L',  'Blush Pink', 30),
            ('XL', 'Black',      10),
            ('XL', 'White',      12),
            ('XL', 'Navy',        0),   # OOS
            ('XL', 'Ash Grey',    0),   # OOS
            ('XL', 'Cream',       4),   # low
            ('XL', 'Burgundy',    0),   # OOS
            ('XL', 'Sky Blue',    0),   # OOS
            ('XL', 'Blush Pink',  8),
        ],
    },
    {
        'name': 'Slim Trousers',
        'category': 'pants',
        'gender': 'women',
        'price': '69.99',
        'description': (
            'Tailored slim trousers with a flattering silhouette. '
            'Versatile for office or casual settings with a premium fabric blend.'
        ),
        'stock': [
            ('S',  'Black',      48),
            ('S',  'White',      10),
            ('S',  'Navy',       22),
            ('S',  'Ash Grey',   18),
            ('S',  'Cream',      25),
            ('S',  'Burgundy',    4),   # low
            ('S',  'Sky Blue',    0),   # OOS
            ('S',  'Blush Pink',  0),   # OOS
            ('M',  'Black',      50),
            ('M',  'White',      14),
            ('M',  'Navy',       30),
            ('M',  'Ash Grey',   22),
            ('M',  'Cream',      28),
            ('M',  'Burgundy',    3),   # low
            ('M',  'Sky Blue',    0),   # OOS
            ('M',  'Blush Pink',  0),   # OOS
            ('L',  'Black',      35),
            ('L',  'White',       5),   # low
            ('L',  'Navy',       16),
            ('L',  'Ash Grey',   10),
            ('L',  'Cream',      12),
            ('L',  'Burgundy',    0),   # OOS
            ('L',  'Sky Blue',    0),   # OOS
            ('L',  'Blush Pink',  0),   # OOS
            ('XL', 'Black',      20),
            ('XL', 'White',       0),   # OOS
            ('XL', 'Navy',        4),   # low
            ('XL', 'Ash Grey',    0),   # OOS
            ('XL', 'Cream',       6),
            ('XL', 'Burgundy',    0),   # OOS
            ('XL', 'Sky Blue',    0),   # OOS
            ('XL', 'Blush Pink',  0),   # OOS
        ],
    },
]


class Command(BaseCommand):
    help = (
        'Wipe all products/variants/inventory and re-seed the catalog with '
        'exactly 4 products and realistic stock levels.'
    )

    def handle(self, *args, **options):
        self.stdout.write('🗑️  Deleting existing products, variants, and inventory...')
        Inventory.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('   Done.'))

        counts = {'products': 0, 'variants': 0, 'in_stock': 0, 'low_stock': 0, 'oos': 0}

        for item in CATALOG:
            product = Product.objects.create(
                name=item['name'],
                category=item['category'],
                gender=item['gender'],
                price=item['price'],
                description=item['description'],
            )
            counts['products'] += 1
            self.stdout.write(f'  ✅ Product: {product.name}')

            for size_name, color_name, qty in item['stock']:
                size = Size.objects.filter(name=size_name).first()
                color = Color.objects.filter(name=color_name).first()

                if not size:
                    self.stdout.write(self.style.WARNING(f'     ⚠️  Size "{size_name}" not found — skipping'))
                    continue
                if not color:
                    self.stdout.write(self.style.WARNING(f'     ⚠️  Color "{color_name}" not found — skipping'))
                    continue

                sku = f'{product.id}-{size_name}-{color_name[:3].upper()}'
                variant, _ = ProductVariant.objects.get_or_create(
                    product=product, size=size, color=color,
                    defaults={'sku': sku},
                )
                Inventory.objects.update_or_create(
                    product_variant=variant,
                    defaults={'quantity': qty, 'low_stock_threshold': 5},
                )
                counts['variants'] += 1
                if qty > 5:
                    counts['in_stock'] += 1
                elif qty > 0:
                    counts['low_stock'] += 1
                else:
                    counts['oos'] += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📦 Catalog reset complete!'))
        self.stdout.write(f"   Products     : {counts['products']}")
        self.stdout.write(f"   Variants     : {counts['variants']}")
        self.stdout.write(f"   In stock     : {counts['in_stock']}")
        self.stdout.write(f"   Low stock    : {counts['low_stock']}")
        self.stdout.write(f"   Out of stock : {counts['oos']}")
