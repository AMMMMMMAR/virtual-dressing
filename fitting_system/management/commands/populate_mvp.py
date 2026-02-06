from django.core.management.base import BaseCommand
from fitting_system.models import Size, Color, Product, ProductVariant, Inventory


class Command(BaseCommand):
    help = 'Populate database with MVP data - minimal clothing sets for men and women'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing existing products...')
        # Clear existing data
        Inventory.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Color.objects.all().delete()  # Clear colors to add new ones
        
        self.stdout.write('Populating database with MVP data...')
        
        # Ensure Sizes exist
        self.stdout.write('Ensuring sizes exist...')
        sizes_data = [
            {'name': 'S', 'chest_min': 85, 'chest_max': 92, 'waist_min': 70, 'waist_max': 77, 
             'shoulder_min': 40, 'shoulder_max': 43, 'height_min': 160, 'height_max': 170},
            {'name': 'M', 'chest_min': 93, 'chest_max': 100, 'waist_min': 78, 'waist_max': 85, 
             'shoulder_min': 44, 'shoulder_max': 47, 'height_min': 168, 'height_max': 178},
            {'name': 'L', 'chest_min': 101, 'chest_max': 108, 'waist_min': 86, 'waist_max': 93, 
             'shoulder_min': 48, 'shoulder_max': 51, 'height_min': 175, 'height_max': 185},
            {'name': 'XL', 'chest_min': 109, 'chest_max': 116, 'waist_min': 94, 'waist_max': 101, 
             'shoulder_min': 52, 'shoulder_max': 55, 'height_min': 180, 'height_max': 190},
        ]
        
        for size_data in sizes_data:
            Size.objects.get_or_create(name=size_data['name'], defaults=size_data)
        
        # Create realistic Colors for each product type
        self.stdout.write('Creating realistic product colors...')
        colors_data = [
            # Classic Cotton Shirt colors (men's shirt - typically white/blue/gray)
            {'name': 'Crisp White', 'hex_code': '#FFFFFF', 'category': 'neutral'},
            {'name': 'Sky Blue', 'hex_code': '#87CEEB', 'category': 'light'},
            {'name': 'Light Gray', 'hex_code': '#D3D3D3', 'category': 'neutral'},
            
            # Casual Denim Jeans colors (blue jeans variations)
            {'name': 'Classic Blue Denim', 'hex_code': '#1560BD', 'category': 'medium'},
            {'name': 'Light Wash Blue', 'hex_code': '#6B8FAF', 'category': 'light'},
            {'name': 'Dark Indigo', 'hex_code': '#2B1B72', 'category': 'dark'},
            
            # Leather Jacket colors (brown/black leather tones)
            {'name': 'Classic Black Leather', 'hex_code': '#1C1C1C', 'category': 'dark'},
            {'name': 'Vintage Brown', 'hex_code': '#654321', 'category': 'medium'},
            {'name': 'Cognac Tan', 'hex_code': '#9A463D', 'category': 'medium'},
            
            # Elegant Blouse colors (women's blouse - soft/elegant tones)
            {'name': 'Ivory Cream', 'hex_code': '#FFFFF0', 'category': 'light'},
            {'name': 'Blush Pink', 'hex_code': '#FFB6C1', 'category': 'light'},
            {'name': 'Soft Lavender', 'hex_code': '#E6E6FA', 'category': 'light'},
            
            # Summer Dress colors (floral/vibrant tones)
            {'name': 'Coral Rose', 'hex_code': '#FF7F7F', 'category': 'warm'},
            {'name': 'Sunny Yellow', 'hex_code': '#FFD700', 'category': 'warm'},
            {'name': 'Ocean Teal', 'hex_code': '#20B2AA', 'category': 'cool'},
            
            # High-Waist Trousers colors (women's pants - office/casual)
            {'name': 'Charcoal Gray', 'hex_code': '#36454F', 'category': 'neutral'},
            {'name': 'Camel Beige', 'hex_code': '#C19A6B', 'category': 'neutral'},
            {'name': 'Navy Classic', 'hex_code': '#000080', 'category': 'dark'},
        ]
        
        colors = {}
        for color_data in colors_data:
            color, _ = Color.objects.get_or_create(name=color_data['name'], defaults=color_data)
            colors[color.name] = color
        
        # Create MVP Products with specific color assignments
        self.stdout.write('Creating MVP products with realistic colors...')
        
        # Define products with their specific colors
        # Each base product has 3 fit variants: slim, regular, oversize
        products_config = [
            # ==========================================
            # MEN'S SHIRTS (3 fit variants)
            # ==========================================
            {
                'product': {
                    'name': 'Slim Fit Cotton Shirt', 
                    'category': 'shirt', 
                    'fit_type': 'slim', 
                    'gender': 'men', 
                    'price': 54.99, 
                    'description': 'Modern slim fit cotton shirt for a sleek, tailored look. Perfect for those who prefer a fitted silhouette.'
                },
                'colors': ['Crisp White', 'Sky Blue', 'Light Gray']
            },
            {
                'product': {
                    'name': 'Classic Cotton Shirt', 
                    'category': 'shirt', 
                    'fit_type': 'regular', 
                    'gender': 'men', 
                    'price': 49.99, 
                    'description': 'A timeless classic cotton shirt perfect for any occasion. Made from 100% premium cotton for maximum comfort and breathability.'
                },
                'colors': ['Crisp White', 'Sky Blue', 'Light Gray']
            },
            {
                'product': {
                    'name': 'Relaxed Cotton Shirt', 
                    'category': 'shirt', 
                    'fit_type': 'oversize', 
                    'gender': 'men', 
                    'price': 52.99, 
                    'description': 'Comfortable relaxed fit cotton shirt with extra room for ease of movement. Perfect for a laid-back style.'
                },
                'colors': ['Crisp White', 'Sky Blue', 'Light Gray']
            },
            
            # ==========================================
            # MEN'S JEANS (3 fit variants)
            # ==========================================
            {
                'product': {
                    'name': 'Slim Fit Jeans', 
                    'category': 'pants', 
                    'fit_type': 'slim', 
                    'gender': 'men', 
                    'price': 84.99, 
                    'description': 'Modern slim fit denim jeans with a streamlined silhouette. Stretch fabric for comfort and mobility.'
                },
                'colors': ['Classic Blue Denim', 'Light Wash Blue', 'Dark Indigo']
            },
            {
                'product': {
                    'name': 'Casual Denim Jeans', 
                    'category': 'pants', 
                    'fit_type': 'regular', 
                    'gender': 'men', 
                    'price': 79.99, 
                    'description': 'Comfortable denim jeans with a classic fit. Durable and stylish for everyday wear with premium denim fabric.'
                },
                'colors': ['Classic Blue Denim', 'Light Wash Blue', 'Dark Indigo']
            },
            {
                'product': {
                    'name': 'Loose Fit Jeans', 
                    'category': 'pants', 
                    'fit_type': 'oversize', 
                    'gender': 'men', 
                    'price': 82.99, 
                    'description': 'Relaxed loose fit jeans for maximum comfort. A contemporary streetwear-inspired silhouette.'
                },
                'colors': ['Classic Blue Denim', 'Light Wash Blue', 'Dark Indigo']
            },
            
            # ==========================================
            # MEN'S JACKETS (3 fit variants)
            # ==========================================
            {
                'product': {
                    'name': 'Fitted Leather Jacket', 
                    'category': 'jacket', 
                    'fit_type': 'slim', 
                    'gender': 'men', 
                    'price': 219.99, 
                    'description': 'Sleek fitted leather jacket with a modern cut. Premium leather for a sharp, tailored appearance.'
                },
                'colors': ['Classic Black Leather', 'Vintage Brown', 'Cognac Tan']
            },
            {
                'product': {
                    'name': 'Leather Jacket', 
                    'category': 'jacket', 
                    'fit_type': 'regular', 
                    'gender': 'men', 
                    'price': 199.99, 
                    'description': 'Premium leather jacket with a classic design. Timeless piece that never goes out of style, crafted from genuine leather.'
                },
                'colors': ['Classic Black Leather', 'Vintage Brown', 'Cognac Tan']
            },
            {
                'product': {
                    'name': 'Oversized Leather Jacket', 
                    'category': 'jacket', 
                    'fit_type': 'oversize', 
                    'gender': 'men', 
                    'price': 229.99, 
                    'description': 'Bold oversized leather jacket for a modern streetwear look. Extra room for layering.'
                },
                'colors': ['Classic Black Leather', 'Vintage Brown', 'Cognac Tan']
            },
            
            # ==========================================
            # WOMEN'S BLOUSES (3 fit variants)
            # ==========================================
            {
                'product': {
                    'name': 'Fitted Blouse', 
                    'category': 'shirt', 
                    'fit_type': 'slim', 
                    'gender': 'women', 
                    'price': 59.99, 
                    'description': 'Elegant fitted blouse with a tailored silhouette. Perfect for a polished, professional look.'
                },
                'colors': ['Ivory Cream', 'Blush Pink', 'Soft Lavender']
            },
            {
                'product': {
                    'name': 'Elegant Blouse', 
                    'category': 'shirt', 
                    'fit_type': 'regular', 
                    'gender': 'women', 
                    'price': 54.99, 
                    'description': 'Sophisticated blouse with delicate details. Perfect for both office and evening wear with premium silk-like fabric.'
                },
                'colors': ['Ivory Cream', 'Blush Pink', 'Soft Lavender']
            },
            {
                'product': {
                    'name': 'Oversized Blouse', 
                    'category': 'shirt', 
                    'fit_type': 'oversize', 
                    'gender': 'women', 
                    'price': 56.99, 
                    'description': 'Flowy oversized blouse for effortless chic style. Comfortable and trendy with relaxed draping.'
                },
                'colors': ['Ivory Cream', 'Blush Pink', 'Soft Lavender']
            },
            
            # ==========================================
            # WOMEN'S DRESSES (3 fit variants)
            # ==========================================
            {
                'product': {
                    'name': 'Fitted Summer Dress', 
                    'category': 'dress', 
                    'fit_type': 'slim', 
                    'gender': 'women', 
                    'price': 94.99, 
                    'description': 'Form-fitting summer dress that accentuates your silhouette. Elegant and flattering for any occasion.'
                },
                'colors': ['Coral Rose', 'Sunny Yellow', 'Ocean Teal']
            },
            {
                'product': {
                    'name': 'Summer Dress', 
                    'category': 'dress', 
                    'fit_type': 'regular', 
                    'gender': 'women', 
                    'price': 89.99, 
                    'description': 'Light and breezy summer dress perfect for warm weather. Comfortable and stylish with a flattering silhouette.'
                },
                'colors': ['Coral Rose', 'Sunny Yellow', 'Ocean Teal']
            },
            {
                'product': {
                    'name': 'Flowy Summer Dress', 
                    'category': 'dress', 
                    'fit_type': 'oversize', 
                    'gender': 'women', 
                    'price': 92.99, 
                    'description': 'Airy flowy dress with a relaxed fit. Bohemian-inspired style perfect for casual summer days.'
                },
                'colors': ['Coral Rose', 'Sunny Yellow', 'Ocean Teal']
            },
            
            # ==========================================
            # WOMEN'S TROUSERS (3 fit variants)
            # ==========================================
            {
                'product': {
                    'name': 'Slim Trousers', 
                    'category': 'pants', 
                    'fit_type': 'slim', 
                    'gender': 'women', 
                    'price': 79.99, 
                    'description': 'Tailored slim fit trousers for a sleek, professional look. Stretch fabric for all-day comfort.'
                },
                'colors': ['Charcoal Gray', 'Camel Beige', 'Navy Classic']
            },
            {
                'product': {
                    'name': 'High-Waist Trousers', 
                    'category': 'pants', 
                    'fit_type': 'regular', 
                    'gender': 'women', 
                    'price': 74.99, 
                    'description': 'Flattering high-waist trousers with a comfortable fit. Versatile for any occasion from office to casual outings.'
                },
                'colors': ['Charcoal Gray', 'Camel Beige', 'Navy Classic']
            },
            {
                'product': {
                    'name': 'Wide-Leg Trousers', 
                    'category': 'pants', 
                    'fit_type': 'oversize', 
                    'gender': 'women', 
                    'price': 77.99, 
                    'description': 'Trendy wide-leg trousers with a relaxed, flowing silhouette. Comfortable and fashion-forward.'
                },
                'colors': ['Charcoal Gray', 'Camel Beige', 'Navy Classic']
            },
        ]

        
        sizes = Size.objects.all()
        
        for config in products_config:
            product_data = config['product']
            product_colors = config['colors']
            
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            
            if created:
                self.stdout.write(f'  Created: {product.name}')
            
            # Create variants with specific colors for this product
            product_sizes = list(sizes)[:3]  # S, M, L
            
            counter = 1
            for size in product_sizes:
                for color_name in product_colors:
                    color = colors.get(color_name)
                    if not color:
                        self.stdout.write(self.style.WARNING(f'    Color not found: {color_name}'))
                        continue
                    
                    sku = f"{product.id}-{size.name}-{color.id}-{counter}"
                    variant, variant_created = ProductVariant.objects.get_or_create(
                        product=product,
                        size=size,
                        color=color,
                        defaults={'sku': sku}
                    )
                    counter += 1
                    
                    # Create inventory with good stock levels
                    if variant_created:
                        import random
                        quantity = random.randint(10, 25)
                        
                        Inventory.objects.create(
                            product_variant=variant,
                            quantity=quantity,
                            low_stock_threshold=5
                        )
            
            self.stdout.write(f'    Colors: {", ".join(product_colors)}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Successfully populated MVP database!'))
        self.stdout.write(f'📦 Created {Product.objects.count()} products (9 men\'s + 9 women\'s with 3 fit types each)')
        self.stdout.write(f'📏 Using {Size.objects.count()} sizes')
        self.stdout.write(f'🎨 Using {Color.objects.count()} colors')
        self.stdout.write(f'🏷️  Created {ProductVariant.objects.count()} product variants')
        self.stdout.write(f'📊 Created {Inventory.objects.count()} inventory records')
        
        # Display product summary with colors and fit type
        self.stdout.write('\n📋 MVP Product Summary:')
        self.stdout.write('  Men\'s Set:')
        for product in Product.objects.filter(gender='men').order_by('category', 'fit_type'):
            colors_list = product.variants.values_list('color__name', flat=True).distinct()
            self.stdout.write(f'    • {product.name} ({product.category} - {product.fit_type})')
            self.stdout.write(f'      Colors: {", ".join(colors_list)}')
        self.stdout.write('  Women\'s Set:')
        for product in Product.objects.filter(gender='women').order_by('category', 'fit_type'):
            colors_list = product.variants.values_list('color__name', flat=True).distinct()
            self.stdout.write(f'    • {product.name} ({product.category} - {product.fit_type})')
            self.stdout.write(f'      Colors: {", ".join(colors_list)}')

