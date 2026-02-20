"""
Recommendation Engine
Generates intelligent clothing recommendations using Gemini AI
and database-backed product matching.

Architecture:
    - Gemini AI: Intelligent size/fit/color recommendations
    - Database: Product matching, inventory checking, variant selection
"""

import logging
from typing import Dict, List, Tuple
from django.db.models import Q

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generates clothing recommendations using Gemini AI for intelligence
    and the product database for matching.
    
    Gemini handles:
        - Size recommendation (considering body shape + garment type)
        - Fit type recommendation
        - Color recommendations (based on skin tone + undertone)
        - Styling advice
    
    Database handles:
        - Finding products with matching size in stock
        - Color variant matching
        - Inventory availability
    """
    
    # Size order for fallback calculations
    SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    
    # Garment-specific measurement priorities (used for fallback)
    GARMENT_MEASUREMENTS = {
        'shirt': {'fit_focus': 'chest'},
        'pants': {'fit_focus': 'waist'},
        'dress': {'fit_focus': 'waist'},
        'jacket': {'fit_focus': 'chest'},
        'skirt': {'fit_focus': 'waist'},
    }
    
    def __init__(self):
        self._gemini = None
    
    @property
    def gemini(self):
        """Lazy-load Gemini client."""
        if self._gemini is None:
            from .gemini_client import get_gemini_client
            self._gemini = get_gemini_client()
        return self._gemini
    
    def recommend_size(self, measurements: Dict[str, float], garment_type: str = 'shirt', body_shape: str = 'rectangle') -> str:
        """
        Recommend clothing size using Gemini AI.
        
        Raises RuntimeError/ValueError if Gemini is unavailable or fails.
        
        Args:
            measurements: Body measurements dict
            garment_type: Type of garment
            body_shape: Body shape classification
            
        Returns:
            Recommended size string (S, M, L, XL, etc.)
        """
        if not self.gemini.available:
            raise RuntimeError("Gemini AI is not available for size recommendation")

        result = self.gemini.get_size_recommendation(
            measurements=measurements,
            garment_type=garment_type,
            body_shape=body_shape
        )
        size = result.get("recommended_size", "M")
        logger.info(f"Gemini size recommendation: {size} for {garment_type} (reason: {result.get('reasoning', 'N/A')})")
        return size
    
    def recommend_fit(self, measurements: Dict[str, float], garment_type: str = 'shirt', body_shape: str = 'rectangle') -> str:
        """
        Recommend fit type using Gemini AI.
        
        Raises RuntimeError if Gemini is unavailable or fails.
        
        Args:
            measurements: Body measurements dict
            
        Returns:
            Recommended fit: 'slim', 'regular', or 'oversize'
        """
        if not self.gemini.available:
            raise RuntimeError("Gemini AI is not available for fit recommendation")

        result = self.gemini.get_size_recommendation(
            measurements=measurements,
            garment_type=garment_type,
            body_shape=body_shape
        )
        fit = result.get("fit_type", "regular")
        if fit in ["slim", "regular", "oversize"]:
            return fit
        return "regular"
    
    def recommend_colors(self, skin_tone: str, undertone: str = 'warm') -> List[str]:
        """
        Recommend colors using Gemini AI.
        
        Raises RuntimeError if Gemini is unavailable or fails.
        
        Args:
            skin_tone: Skin tone category
            undertone: Skin undertone (warm/cool)
            
        Returns:
            List of recommended color names
        """
        if not self.gemini.available:
            raise RuntimeError("Gemini AI is not available for color recommendation")

        colors = self.gemini.get_color_recommendations(
            skin_tone=skin_tone,
            undertone=undertone
        )
        if colors:
            return colors
        raise ValueError("Gemini returned empty color recommendations")
    
    def recommend_products(
        self,
        measurements: Dict[str, float],
        skin_tone: str,
        gender: str = 'unisex',
        body_shape: str = 'rectangle',
        limit: int = 10
    ) -> List[Tuple[object, int]]:
        """
        Recommend products based on Gemini AI analysis + database matching.
        
        Args:
            measurements: Body measurements dict
            skin_tone: Skin tone category
            gender: 'men', 'women', or 'unisex'
            body_shape: Body shape classification
            limit: Maximum number of recommendations
            
        Returns:
            List of tuples (Product, priority_score)
        """
        from fitting_system.models import Product, ProductVariant, Color
        
        # Get AI-powered recommendations
        recommended_size = self.recommend_size(measurements, body_shape=body_shape)
        recommended_fit = self.recommend_fit(measurements, body_shape=body_shape)
        recommended_color_names = self.recommend_colors(skin_tone)
        
        # Get recommended color objects from DB
        recommended_colors = Color.objects.filter(name__in=recommended_color_names)
        
        # Filter products by gender
        products = Product.objects.filter(
            Q(gender=gender) | Q(gender='unisex')
        )
        
        recommendations = []
        
        for product in products:
            # Check availability
            available_variants = ProductVariant.objects.filter(
                product=product,
                inventory__quantity__gt=0
            )
            
            if not available_variants.exists():
                continue
            
            priority = 0
            
            # Higher priority for matching fit type
            if product.fit_type == recommended_fit:
                priority += 15
            
            # Higher priority for matching size in stock
            size_variants = available_variants.filter(size__name=recommended_size)
            if size_variants.exists():
                priority += 10
            
            # Higher priority for matching colors
            matching_color_variants = available_variants.filter(
                color__in=recommended_colors
            )
            if matching_color_variants.exists():
                priority += 10
            
            priority += 5  # Base priority
            
            recommendations.append((product, priority))
        
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
        Uses Gemini AI for size/color/fit recommendations, then matches against inventory.
        
        Args:
            body_scan: BodyScan model instance
            gender: Optional gender filter
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
        
        # Get Gemini-powered recommendations
        recommended_color_names = self.recommend_colors(body_scan.skin_tone, undertone)
        recommended_fit = self.recommend_fit(measurements, body_shape=body_shape)
        
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
            # Get Gemini-powered garment-specific size recommendation
            rec_size = self.recommend_size(
                measurements, 
                garment_type=product.category, 
                body_shape=body_shape
            )
            
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
        
        # Sort: fit matches first, then perfect matches, then by name
        matching_products.sort(key=lambda x: (
            not x['fit_matches_recommendation'],
            not x['is_perfect_match'], 
            x['product'].name
        ))
        
        return matching_products[:limit]
    
    def generate_recommendations_for_scan(self, body_scan) -> List[object]:
        """
        Generate and save recommendations for a body scan using Gemini AI.
        
        Args:
            body_scan: BodyScan model instance
            
        Returns:
            List of created Recommendation objects
        """
        from fitting_system.models import Recommendation
        
        # Build measurements dict
        measurements = {
            'height': float(body_scan.height),
            'chest': float(body_scan.chest),
            'waist': float(body_scan.waist),
            'shoulder_width': float(body_scan.shoulder_width)
        }
        
        if body_scan.hip:
            measurements['hip'] = float(body_scan.hip)
        if body_scan.torso_length:
            measurements['torso_length'] = float(body_scan.torso_length)
        if body_scan.arm_length:
            measurements['arm_length'] = float(body_scan.arm_length)
        if body_scan.inseam:
            measurements['inseam'] = float(body_scan.inseam)
        
        body_shape = getattr(body_scan, 'body_shape', 'rectangle') or 'rectangle'
        undertone = getattr(body_scan, 'undertone', 'warm')
        
        # Get Gemini-powered recommendations
        base_recommended_size = self.recommend_size(measurements, body_shape=body_shape)
        recommended_fit = self.recommend_fit(measurements, body_shape=body_shape)
        recommended_colors = self.recommend_colors(body_scan.skin_tone, undertone)
        
        # Get product recommendations
        product_recommendations = []
        
        for gender in ['men', 'women', 'unisex']:
            recs = self.recommend_products(
                measurements,
                body_scan.skin_tone,
                gender=gender,
                body_shape=body_shape,
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
            # Get Gemini garment-specific size recommendation
            recommended_size = self.recommend_size(
                measurements, 
                garment_type=product.category,
                body_shape=body_shape
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
    
    # _fallback_recommend_size REMOVED – Gemini AI is the sole source.
