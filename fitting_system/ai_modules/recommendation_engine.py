"""
Recommendation Engine
Generates intelligent clothing recommendations based on measurements and skin tone
"""

from typing import Dict, List, Tuple
from django.db.models import Q


class RecommendationEngine:
    """Generates clothing recommendations based on body measurements and skin tone"""
    
    FIT_RECOMMENDATIONS = {
        'slim': {'min_ratio': 1.3, 'max_ratio': 2.0},
        'regular': {'min_ratio': 1.1, 'max_ratio': 1.3},
        'oversize': {'min_ratio': 0.0, 'max_ratio': 1.1}
    }
    
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
        
        chest = measurements.get('chest', 0)
        waist = measurements.get('waist', 0)
        height = measurements.get('height', 0)
        shoulder = measurements.get('shoulder_width', 0)
        
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
        
        # Filter products by gender and fit
        products = Product.objects.filter(
            Q(gender=gender) | Q(gender='unisex'),
            fit_type=recommended_fit
        )
        
        recommendations = []
        
        for product in products:
            # Check if product has available variants with recommended size and colors
            available_variants = ProductVariant.objects.filter(
                product=product,
                size__name=recommended_size,
                inventory__quantity__gt=0  # Only available items
            )
            
            if not available_variants.exists():
                continue
            
            # Calculate priority score
            priority = 0
            
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
    
    def generate_recommendations_for_scan(self, body_scan) -> List[object]:
        """
        Generate and save recommendations for a body scan
        
        Args:
            body_scan: BodyScan model instance
            
        Returns:
            List of created Recommendation objects
        """
        from fitting_system.models import Recommendation
        
        measurements = {
            'height': float(body_scan.height),
            'chest': float(body_scan.chest),
            'waist': float(body_scan.waist),
            'shoulder_width': float(body_scan.shoulder_width)
        }
        
        recommended_size = self.recommend_size(measurements)
        recommended_fit = self.recommend_fit(measurements)
        # Use undertone for color recommendations (with backward compatibility)
        undertone = getattr(body_scan, 'undertone', 'warm')
        recommended_colors = self.recommend_colors(body_scan.skin_tone, undertone)
        
        # Get product recommendations
        # Try to infer gender from product availability (for prototype)
        # In production, you'd ask the customer
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
        
        # Create Recommendation objects
        recommendation_objects = []
        for product, priority in unique_recommendations[:10]:
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
