from django.core.management.base import BaseCommand
from fitting_system.models import Size, Color, Product, ProductVariant, Inventory


class Command(BaseCommand):
    help = 'Populate database with initial data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating database with initial data...')
        
        # Create Sizes
        self.stdout.write('Creating sizes...')
        sizes_data = [
            {'name': 'S', 'chest_min': 85, 'chest_max': 92, 'waist_min': 70, 'waist_max': 77, 
             'shoulder_min': 40, 'shoulder_max': 43, 'height_min': 160, 'height_max': 170},
            {'name': 'M', 'chest_min': 93, 'chest_max': 100, 'waist_min': 78, 'waist_max': 85, 
             'shoulder_min': 44, 'shoulder_max': 47, 'height_min': 168, 'height_max': 178},
            {'name': 'L', 'chest_min': 101, 'chest_max': 108, 'waist_min': 86, 'waist_max': 93, 
             'shoulder_min': 48, 'shoulder_max': 51, 'height_min': 175, 'height_max': 185},
            {'name': 'XL', 'chest_min': 109, 'chest_max': 116, 'waist_min': 94, 'waist_max': 101, 
             'shoulder_min': 52, 'shoulder_max': 55, 'height_min': 180, 'height_max': 190},
            {'name': 'XXL', 'chest_min': 117, 'chest_max': 125, 'waist_min': 102, 'waist_max': 110, 
             'shoulder_min': 56, 'shoulder_max': 60, 'height_min': 185, 'height_max': 195},
        ]
        
        for size_data in sizes_data:
            Size.objects.get_or_create(name=size_data['name'], defaults=size_data)
        
        # Create Colors
        self.stdout.write('Creating colors...')
        colors_data = [
            # Light skin tone colors
            {'name': 'Pastel Pink', 'hex_code': '#FFD1DC', 'category': 'light'},
            {'name': 'Light Blue', 'hex_code': '#ADD8E6', 'category': 'light'},
            {'name': 'Lavender', 'hex_code': '#E6E6FA', 'category': 'light'},
            {'name': 'Mint Green', 'hex_code': '#98FF98', 'category': 'light'},
            
            # Medium skin tone colors
            {'name': 'Earth Brown', 'hex_code': '#8B4513', 'category': 'medium'},
            {'name': 'Olive Green', 'hex_code': '#808000', 'category': 'medium'},
            {'name': 'Burgundy', 'hex_code': '#800020', 'category': 'medium'},
            {'name': 'Mustard Yellow', 'hex_code': '#FFDB58', 'category': 'medium'},
            
            # Dark skin tone colors
            {'name': 'Bright White', 'hex_code': '#FFFFFF', 'category': 'dark'},
            {'name': 'Vibrant Red', 'hex_code': '#FF0000', 'category': 'dark'},
            {'name': 'Electric Blue', 'hex_code': '#7DF9FF', 'category': 'dark'},
            {'name': 'Sunny Yellow', 'hex_code': '#FFD700', 'category': 'dark'},
            
            # Neutral colors
            {'name': 'Black', 'hex_code': '#000000', 'category': 'neutral'},
            {'name': 'White', 'hex_code': '#FFFFFF', 'category': 'neutral'},
            {'name': 'Gray', 'hex_code': '#808080', 'category': 'neutral'},
            {'name': 'Navy Blue', 'hex_code': '#000080', 'category': 'neutral'},
        ]
        
        for color_data in colors_data:
            Color.objects.get_or_create(name=color_data['name'], defaults=color_data)
        
        # Create Products
        self.stdout.write('Creating products...')
        products_data = [
            # Men's products
            {'name': 'Classic Cotton Shirt', 'category': 'shirt', 'fit_type': 'regular', 'gender': 'men', 
             'price': 49.99, 'description': 'A timeless classic cotton shirt perfect for any occasion. Made from 100% premium cotton for maximum comfort.'},
            {'name': 'Slim Fit Dress Shirt', 'category': 'shirt', 'fit_type': 'slim', 'gender': 'men', 
             'price': 59.99, 'description': 'Modern slim fit dress shirt with a tailored silhouette. Perfect for professional settings.'},
            {'name': 'Casual Denim Jeans', 'category': 'pants', 'fit_type': 'regular', 'gender': 'men', 
             'price': 79.99, 'description': 'Comfortable denim jeans with a classic fit. Durable and stylish for everyday wear.'},
            {'name': 'Slim Fit Chinos', 'category': 'pants', 'fit_type': 'slim', 'gender': 'men', 
             'price': 69.99, 'description': 'Versatile slim fit chinos that pair well with any outfit. Perfect blend of style and comfort.'},
            {'name': 'Leather Jacket', 'category': 'jacket', 'fit_type': 'regular', 'gender': 'men', 
             'price': 199.99, 'description': 'Premium leather jacket with a classic design. Timeless piece that never goes out of style.'},
            
            # Women's products
            {'name': 'Elegant Blouse', 'category': 'shirt', 'fit_type': 'regular', 'gender': 'women', 
             'price': 54.99, 'description': 'Sophisticated blouse with delicate details. Perfect for both office and evening wear.'},
            {'name': 'Fitted Blazer', 'category': 'jacket', 'fit_type': 'slim', 'gender': 'women', 
             'price': 129.99, 'description': 'Tailored blazer that adds polish to any outfit. Professional yet stylish.'},
            {'name': 'High-Waist Trousers', 'category': 'pants', 'fit_type': 'regular', 'gender': 'women', 
             'price': 74.99, 'description': 'Flattering high-waist trousers with a comfortable fit. Versatile for any occasion.'},
            {'name': 'Summer Dress', 'category': 'dress', 'fit_type': 'regular', 'gender': 'women', 
             'price': 89.99, 'description': 'Light and breezy summer dress perfect for warm weather. Comfortable and stylish.'},
            {'name': 'Pencil Skirt', 'category': 'skirt', 'fit_type': 'slim', 'gender': 'women', 
             'price': 49.99, 'description': 'Classic pencil skirt with a flattering silhouette. Essential wardrobe piece.'},
        ]
        
        products = []
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            products.append(product)
        
        # Create Product Variants and Inventory
        self.stdout.write('Creating product variants and inventory...')
        sizes = Size.objects.all()
        colors = Color.objects.all()[:8]  # Use first 8 colors
        
        for product in products:
            # Create 2-3 size variants per product
            product_sizes = list(sizes)[1:4]  # M, L, XL
            product_colors = list(colors)[:3]  # First 3 colors
            
            counter = 1
            for size in product_sizes:
                for color in product_colors:
                    sku = f"{product.id}-{size.name}-{color.id}-{counter}"
                    variant, created = ProductVariant.objects.get_or_create(
                        product=product,
                        size=size,
                        color=color,
                        defaults={'sku': sku}
                    )
                    counter += 1
                    
                    # Create inventory for this variant
                    if created:
                        import random
                        quantity = random.randint(0, 20)  # Random stock between 0-20
                        Inventory.objects.create(
                            product_variant=variant,
                            quantity=quantity,
                            low_stock_threshold=5
                        )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated database!'))
        self.stdout.write(f'Created {Size.objects.count()} sizes')
        self.stdout.write(f'Created {Color.objects.count()} colors')
        self.stdout.write(f'Created {Product.objects.count()} products')
        self.stdout.write(f'Created {ProductVariant.objects.count()} product variants')
        self.stdout.write(f'Created {Inventory.objects.count()} inventory records')
