"""
Recommendation Engine
Generates intelligent clothing recommendations based on measurements and skin tone
"""

from typing import Dict, List, Tuple
from django.db.models import Q


class RecommendationEngine:
    """Generates clothing recommendations based on body measurements and skin tone"""
    
    FIT_RECOMMENDATIONS = {
        'slim': {'min_ratio': 1.4, 'max_ratio': 2.5},
        'regular': {'min_ratio': 1.15, 'max_ratio': 1.4},
        'oversize': {'min_ratio': 0.0, 'max_ratio': 1.15}
    }
    
    # Conversion factor for width measurements to circumference estimates
    # Body scan captures width (front-to-back), multiply by ~2 to estimate circumference
    WIDTH_TO_CIRCUMFERENCE_FACTOR = 2.0
    
    # Garment-specific measurement priorities
    GARMENT_MEASUREMENTS = {
        'shirt': {
            'primary': ['chest', 'shoulder_width'],
            'secondary': ['arm_length', 'torso_length'],
            'fit_focus': 'chest',
        },
        'pants': {
            'primary': ['waist', 'hip', 'inseam'],
            'secondary': ['thigh'],
            'fit_focus': 'waist',
        },
        'dress': {
            'primary': ['chest', 'waist', 'hip'],
            'secondary': ['torso_length'],
            'fit_focus': 'waist',
        },
        'jacket': {
            'primary': ['chest', 'shoulder_width'],
            'secondary': ['arm_length', 'torso_length'],
            'fit_focus': 'chest',
        },
        'skirt': {
            'primary': ['waist', 'hip'],
            'secondary': ['torso_length'],
            'fit_focus': 'waist',
        },
    }
    
    # Body shape adjustments for size recommendations
    # Positive = size up, Negative = size down
    BODY_SHAPE_ADJUSTMENTS = {
        'inverted_triangle': {'shirt': 1, 'jacket': 1, 'pants': -1, 'dress': 0, 'skirt': -1},
        'triangle': {'shirt': -1, 'jacket': 0, 'pants': 1, 'dress': 0, 'skirt': 1},
        'oval': {'shirt': 1, 'jacket': 1, 'pants': 1, 'dress': 1, 'skirt': 1},
        'hourglass': {'shirt': 0, 'jacket': 0, 'pants': 0, 'dress': -1, 'skirt': 0},
        'rectangle': {'shirt': 0, 'jacket': 0, 'pants': 0, 'dress': 0, 'skirt': 0},
    }
    
    # Size order for adjustment calculations
    SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    
    def __init__(self):
        pass
    
    def recommend_size(self, measurements: Dict[str, float]) -> str:
        """
        Recommend clothing size based on measurements
        
        Args:
            measurements: Dict with 'height', 'chest', 'waist', 'shoulder_width'
            
        Returns:
            Recommended size (S, M, L, XL, XXL)
        """
        from fitting_system.models import Size
        
        # Convert width measurements to circumference estimates
        # Body scan captures width, but Size model uses circumference
        chest = measurements.get('chest', 0) * self.WIDTH_TO_CIRCUMFERENCE_FACTOR
        waist = measurements.get('waist', 0) * self.WIDTH_TO_CIRCUMFERENCE_FACTOR
        height = measurements.get('height', 0)  # Height doesn't need conversion
        shoulder = measurements.get('shoulder_width', 0) * self.WIDTH_TO_CIRCUMFERENCE_FACTOR
        
        # Find matching size based on measurements
        # Priority: chest > waist > shoulder > height
        matching_sizes = Size.objects.filter(
            chest_min__lte=chest,
            chest_max__gte=chest,
            waist_min__lte=waist,
            waist_max__gte=waist
        )
        
        if matching_sizes.exists():
            return matching_sizes.first().name
        
        # If no exact match, find closest size based on chest measurement
        all_sizes = Size.objects.all().order_by('chest_min')
        
        if not all_sizes.exists():
            return 'M'  # Fallback if no sizes in database
        
        if chest < all_sizes.first().chest_min:
            return all_sizes.first().name  # Smallest size
        elif chest > all_sizes.last().chest_max:
            return all_sizes.last().name  # Largest size
        else:
            # Find closest size
            for size in all_sizes:
                if size.chest_min <= chest <= size.chest_max:
                    return size.name
        
        # Default fallback
        return 'M'

    
    def recommend_size_for_garment(
        self, 
        measurements: Dict[str, float], 
        garment_type: str,
        body_shape: str = 'rectangle'
    ) -> str:
        """
        Recommend size based on garment-specific measurements and body shape.
        
        Args:
            measurements: Body measurements dict
            garment_type: Type of garment ('shirt', 'pants', 'dress', 'jacket', 'skirt')
            body_shape: Body shape classification
            
        Returns:
            Recommended size with body shape adjustment applied
        """
        from fitting_system.models import Size
        
        # Get garment configuration
        config = self.GARMENT_MEASUREMENTS.get(garment_type, self.GARMENT_MEASUREMENTS['shirt'])
        fit_focus = config['fit_focus']
        
        # Convert width measurement to circumference estimate
        focus_value = measurements.get(fit_focus, 0) * self.WIDTH_TO_CIRCUMFERENCE_FACTOR
        
        # Find base size using the focus measurement
        if fit_focus == 'chest':
            matching_sizes = Size.objects.filter(
                chest_min__lte=focus_value,
                chest_max__gte=focus_value
            )
        elif fit_focus == 'waist':
            matching_sizes = Size.objects.filter(
                waist_min__lte=focus_value,
                waist_max__gte=focus_value
            )
        else:
            matching_sizes = Size.objects.filter(
                chest_min__lte=focus_value,
                chest_max__gte=focus_value
            )
        
        if matching_sizes.exists():
            base_size = matching_sizes.first().name
        else:
            # Fallback to generic size recommendation
            base_size = self.recommend_size(measurements)
        
        # Apply body shape adjustment
        adjusted_size = self.apply_body_shape_adjustment(base_size, body_shape, garment_type)
        
        return adjusted_size

    
    def apply_body_shape_adjustment(self, base_size: str, body_shape: str, garment_type: str) -> str:
        """
        Adjust size based on body shape.
        
        Args:
            base_size: The base recommended size
            body_shape: Body shape classification
            garment_type: Type of garment
            
        Returns:
            Adjusted size
        """
        adjustment = self.BODY_SHAPE_ADJUSTMENTS.get(body_shape, {}).get(garment_type, 0)
        
        if adjustment == 0:
            return base_size
        
        try:
            current_index = self.SIZE_ORDER.index(base_size.upper())
            new_index = current_index + adjustment
            
            # Clamp to valid range
            new_index = max(0, min(new_index, len(self.SIZE_ORDER) - 1))
            
            return self.SIZE_ORDER[new_index]
        except ValueError:
            # Size not found in order list
            return base_size
    
    def recommend_fit(self, measurements: Dict[str, float]) -> str:
        """
        Recommend fit type based on body proportions
        
        Args:
            measurements: Dict with 'chest' and 'waist'
            
        Returns:
            Recommended fit: 'slim', 'regular', or 'oversize'
        """
        chest = measurements.get('chest', 0)
        waist = measurements.get('waist', 0)
        
        if waist == 0:
            return 'regular'
        
        ratio = chest / waist
        
        # Determine fit based on chest-to-waist ratio
        if ratio >= self.FIT_RECOMMENDATIONS['slim']['min_ratio']:
            return 'slim'
        elif ratio >= self.FIT_RECOMMENDATIONS['regular']['min_ratio']:
            return 'regular'
        else:
            return 'oversize'
    
    def recommend_colors(self, skin_tone: str, undertone: str = 'warm') -> List[str]:
        """
        Recommend colors based on skin tone and undertone
        
        Args:
            skin_tone: Skin tone category (e.g., 'very_light', 'light', 'intermediate', 'tan', 'dark')
            undertone: Skin undertone ('warm' or 'cool')
            
        Returns:
            List of recommended color names
        """
        from fitting_system.ai_modules.skin_tone import SkinToneAnalyzer
        
        analyzer = SkinToneAnalyzer()
        return analyzer.get_recommended_colors(skin_tone, undertone)
    
    def recommend_products(
        self,
        measurements: Dict[str, float],
        skin_tone: str,
        gender: str = 'unisex',
        limit: int = 10
    ) -> List[Tuple[object, int]]:
        """
        Recommend products based on measurements, skin tone, and availability
        
        Args:
            measurements: Body measurements dict
            skin_tone: Skin tone category
            gender: 'men', 'women', or 'unisex'
            limit: Maximum number of recommendations
            
        Returns:
            List of tuples (Product, priority_score)
        """
        from fitting_system.models import Product, ProductVariant, Color
        
        # Get recommendations
        recommended_size = self.recommend_size(measurements)
        recommended_fit = self.recommend_fit(measurements)
        recommended_color_names = self.recommend_colors(skin_tone)
        
        # Get recommended color objects
        recommended_colors = Color.objects.filter(name__in=recommended_color_names)
        
        # Filter products by gender only (not strict fit filtering)
        # This ensures we always have products to recommend
        products = Product.objects.filter(
            Q(gender=gender) | Q(gender='unisex')
        )
        
        recommendations = []
        
        for product in products:
            # Check if product has any available variants
            available_variants = ProductVariant.objects.filter(
                product=product,
                inventory__quantity__gt=0  # Only available items
            )
            
            if not available_variants.exists():
                continue
            
            # Calculate priority score
            priority = 0
            
            # Higher priority for matching fit type
            if product.fit_type == recommended_fit:
                priority += 15
            
            # Higher priority for products with recommended size in stock
            size_variants = available_variants.filter(size__name=recommended_size)
            if size_variants.exists():
                priority += 10
            
            # Higher priority for products with recommended colors
            matching_color_variants = available_variants.filter(
                color__in=recommended_colors
            )
            if matching_color_variants.exists():
                priority += 10
            
            # Add base priority
            priority += 5
            
            recommendations.append((product, priority))
        
        # Sort by priority (descending) and limit results
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:limit]
    
    def get_matching_product_variants(
        self,
        body_scan,
        gender: str = None,
        limit: int = 6
    ) -> List[Dict]:
        """
        Get actual products from store with specific size and color recommendations.
        
        This method finds products that:
        1. Have the user's recommended size in stock
        2. Preferably have a color that matches their skin tone
        3. Match the user's preferred gender (if specified)
        4. Prioritize products matching recommended fit type
        
        Args:
            body_scan: BodyScan model instance
            gender: Optional gender filter ('men', 'women', or None for all)
            limit: Maximum number of products to return
            
        Returns:
            List of dicts with product, size, color, and fit message
        """
        from fitting_system.models import Product, ProductVariant, Color, Size
        
        # Build measurements dict
        measurements = {
            'height': float(body_scan.height),
            'chest': float(body_scan.chest),
            'waist': float(body_scan.waist),
            'shoulder_width': float(body_scan.shoulder_width)
        }
        if body_scan.hip:
            measurements['hip'] = float(body_scan.hip)
        if body_scan.inseam:
            measurements['inseam'] = float(body_scan.inseam)
        if body_scan.torso_length:
            measurements['torso_length'] = float(body_scan.torso_length)
        if body_scan.arm_length:
            measurements['arm_length'] = float(body_scan.arm_length)
        
        body_shape = getattr(body_scan, 'body_shape', 'rectangle') or 'rectangle'
        undertone = getattr(body_scan, 'undertone', 'warm')
        
        # Get recommended colors for user's skin tone
        recommended_color_names = self.recommend_colors(body_scan.skin_tone, undertone)
        recommended_fit = self.recommend_fit(measurements)
        
        # Find matching products
        matching_products = []
        
        # Query products with optional gender filter
        if gender and gender in ['men', 'women']:
            products = Product.objects.filter(
                Q(gender=gender) | Q(gender='unisex')
            )
        else:
            products = Product.objects.all()
        
        for product in products:
            # Get garment-specific size for this product
            rec_size = self.recommend_size_for_garment(
                measurements, 
                product.category, 
                body_shape
            )
            
            # Check if product fit matches recommended fit
            fit_matches = product.fit_type == recommended_fit
            
            # Priority 1: Exact size + recommended color + in stock
            matching_variant = ProductVariant.objects.filter(
                product=product,
                size__name=rec_size,
                color__name__in=recommended_color_names,
                inventory__quantity__gt=0
            ).select_related('size', 'color', 'product').first()
            
            if matching_variant:
                matching_products.append({
                    'product': product,
                    'variant': matching_variant,
                    'recommended_size': rec_size,
                    'recommended_color': matching_variant.color.name,
                    'color_hex': matching_variant.color.hex_code,
                    'fit_type': product.fit_type,
                    'is_perfect_match': True,
                    'fit_matches_recommendation': fit_matches,
                    'recommended_fit': recommended_fit,
                    'fit_message': f"This {product.category} in size {rec_size} with {matching_variant.color.name} will fit you perfectly!"
                })
                continue
            
            # Priority 2: Exact size + any color in stock
            size_only_variant = ProductVariant.objects.filter(
                product=product,
                size__name=rec_size,
                inventory__quantity__gt=0
            ).select_related('size', 'color', 'product').first()
            
            if size_only_variant:
                matching_products.append({
                    'product': product,
                    'variant': size_only_variant,
                    'recommended_size': rec_size,
                    'recommended_color': size_only_variant.color.name,
                    'color_hex': size_only_variant.color.hex_code,
                    'fit_type': product.fit_type,
                    'is_perfect_match': False,
                    'fit_matches_recommendation': fit_matches,
                    'recommended_fit': recommended_fit,
                    'fit_message': f"This {product.category} in size {rec_size} will fit you great!"
                })
        
        # Sort: products matching recommended fit first, then perfect matches, then by name
        matching_products.sort(key=lambda x: (
            not x['fit_matches_recommendation'],
            not x['is_perfect_match'], 
            x['product'].name
        ))
        
        return matching_products[:limit]

    
    def generate_recommendations_for_scan(self, body_scan) -> List[object]:
        """
        Generate and save recommendations for a body scan.
        Uses garment-specific sizing and body shape adjustments.
        
        Args:
            body_scan: BodyScan model instance
            
        Returns:
            List of created Recommendation objects
        """
        from fitting_system.models import Recommendation
        
        # Build measurements dict including new fashion measurements
        measurements = {
            'height': float(body_scan.height),
            'chest': float(body_scan.chest),
            'waist': float(body_scan.waist),
            'shoulder_width': float(body_scan.shoulder_width)
        }
        
        # Add fashion-specific measurements if available
        if body_scan.hip:
            measurements['hip'] = float(body_scan.hip)
        if body_scan.torso_length:
            measurements['torso_length'] = float(body_scan.torso_length)
        if body_scan.arm_length:
            measurements['arm_length'] = float(body_scan.arm_length)
        if body_scan.inseam:
            measurements['inseam'] = float(body_scan.inseam)
        
        # Get body shape (with backward compatibility)
        body_shape = getattr(body_scan, 'body_shape', 'rectangle') or 'rectangle'
        
        # Get base recommendations
        base_recommended_size = self.recommend_size(measurements)
        recommended_fit = self.recommend_fit(measurements)
        
        # Use undertone for color recommendations (with backward compatibility)
        undertone = getattr(body_scan, 'undertone', 'warm')
        recommended_colors = self.recommend_colors(body_scan.skin_tone, undertone)
        
        # Get product recommendations
        product_recommendations = []
        
        for gender in ['men', 'women', 'unisex']:
            recs = self.recommend_products(
                measurements,
                body_scan.skin_tone,
                gender=gender,
                limit=10
            )
            product_recommendations.extend(recs)
        
        # Remove duplicates and sort by priority
        seen_products = set()
        unique_recommendations = []
        for product, priority in product_recommendations:
            if product.id not in seen_products:
                seen_products.add(product.id)
                unique_recommendations.append((product, priority))
        
        unique_recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # Create Recommendation objects with garment-specific sizing
        recommendation_objects = []
        for product, priority in unique_recommendations[:10]:
            # Get garment-specific size with body shape adjustment
            recommended_size = self.recommend_size_for_garment(
                measurements, 
                product.category,
                body_shape
            )
            
            rec = Recommendation.objects.create(
                body_scan=body_scan,
                product=product,
                recommended_size=recommended_size,
                recommended_fit=recommended_fit,
                recommended_colors=', '.join(recommended_colors[:5]),
                priority=priority
            )
            recommendation_objects.append(rec)
        
        return recommendation_objects
