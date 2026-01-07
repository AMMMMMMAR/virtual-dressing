from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import base64
import numpy as np
import cv2
from io import BytesIO
from PIL import Image

from .models import Product, ProductVariant, Inventory, BodyScan, Recommendation, Size, Color
from .ai_modules.body_measurement import BodyMeasurementEstimator
from .ai_modules.skin_tone import SkinToneAnalyzer
from .ai_modules.recommendation_engine import RecommendationEngine


# Global estimator instance
_MEASUREMENT_ESTIMATOR = None

def get_estimator():
    """Get or initialize the global estimator instance"""
    global _MEASUREMENT_ESTIMATOR
    if _MEASUREMENT_ESTIMATOR is None:
        _MEASUREMENT_ESTIMATOR = BodyMeasurementEstimator()
    return _MEASUREMENT_ESTIMATOR


def index(request):
    """Landing page"""
    return render(request, 'index.html')


def scan(request):
    """Camera interface and scanning workflow"""
    return render(request, 'scan.html')


@csrf_exempt
def process_scan(request):
    """Process captured images with AI modules"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        front_image_data = data.get('front_image')
        side_image_data = data.get('side_image')
        
        if not front_image_data:
            return JsonResponse({'error': 'Front image is required'}, status=400)
        
        # Decode base64 images
        front_image = decode_base64_image(front_image_data)
        side_image = decode_base64_image(side_image_data) if side_image_data else None
        
        # Estimate body measurements
        measurement_estimator = get_estimator()
        measurements = measurement_estimator.estimate_from_front_and_side(
            front_image, 
            side_image
        )
        
        # Analyze skin tone
        skin_tone_analyzer = SkinToneAnalyzer()
        skin_tone = skin_tone_analyzer.analyze_skin_tone(front_image)
        
        # Create BodyScan record
        body_scan = BodyScan.objects.create(
            height=measurements['height'],
            shoulder_width=measurements['shoulder_width'],
            chest=measurements['chest'],
            waist=measurements['waist'],
            skin_tone=skin_tone
        )
        
        # Generate recommendations
        rec_engine = RecommendationEngine()
        recommendations = rec_engine.generate_recommendations_for_scan(body_scan)
        
        return JsonResponse({
            'success': True,
            'session_id': str(body_scan.session_id),
            'measurements': measurements,
            'skin_tone': skin_tone
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Processing failed: {str(e)}'}, status=500)


@csrf_exempt
def analyze_frame(request):
    """Analyze single frame for real-time feedback"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            return JsonResponse({'error': 'Image is required'}, status=400)
        
        # Decode image
        image = decode_base64_image(image_data)
        
        # Analyze pose
        estimator = get_estimator()
        result = estimator.analyze_pose(image)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': str(e), 'detected': False}, status=500)


def recommendations(request, session_id):
    """Display results and recommendations"""
    body_scan = get_object_or_404(BodyScan, session_id=session_id)
    recommendations = body_scan.recommendations.all()
    
    # Get recommended colors
    rec_engine = RecommendationEngine()
    recommended_colors = rec_engine.recommend_colors(body_scan.skin_tone)
    
    context = {
        'body_scan': body_scan,
        'recommendations': recommendations,
        'recommended_colors': recommended_colors[:5],
        'recommended_size': recommendations.first().recommended_size if recommendations.exists() else 'N/A',
        'recommended_fit': recommendations.first().recommended_fit if recommendations.exists() else 'N/A',
    }
    
    return render(request, 'recommendations.html', context)


def inventory_dashboard(request):
    """Inventory management dashboard"""
    # Get all product variants with inventory
    variants = ProductVariant.objects.select_related(
        'product', 'size', 'color', 'inventory'
    ).all()
    
    # Separate by stock status
    in_stock = []
    low_stock = []
    out_of_stock = []
    
    for variant in variants:
        try:
            if variant.inventory.is_out_of_stock:
                out_of_stock.append(variant)
            elif variant.inventory.is_low_stock:
                low_stock.append(variant)
            else:
                in_stock.append(variant)
        except Inventory.DoesNotExist:
            out_of_stock.append(variant)
    
    context = {
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_variants': variants.count(),
    }
    
    return render(request, 'inventory.html', context)


def store(request):
    """Online store product catalog"""
    # Get filter parameters
    category = request.GET.get('category', '')
    gender = request.GET.get('gender', '')
    search = request.GET.get('search', '')
    
    # Base query
    products = Product.objects.all()
    
    # Apply filters
    if category:
        products = products.filter(category=category)
    if gender:
        products = products.filter(Q(gender=gender) | Q(gender='unisex'))
    if search:
        products = products.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    # Get unique categories and genders for filters (remove duplicates)
    categories = Product.objects.values_list('category', flat=True).distinct().order_by('category')
    genders = Product.objects.values_list('gender', flat=True).distinct().order_by('gender')
    
    context = {
        'products': products,
        'categories': categories,
        'genders': genders,
        'selected_category': category,
        'selected_gender': gender,
        'search_query': search,
    }
    
    return render(request, 'store.html', context)


def product_detail(request, product_id):
    """Product detail page"""
    product = get_object_or_404(Product, id=product_id)
    
    # Get all variants for this product
    variants = product.variants.select_related('size', 'color', 'inventory').all()
    
    # Get available sizes and colors
    available_sizes = set()
    available_colors = set()
    
    for variant in variants:
        try:
            if variant.inventory.is_available:
                available_sizes.add(variant.size)
                available_colors.add(variant.color)
        except Inventory.DoesNotExist:
            pass
    
    # Get related products (same category, different product)
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'variants': variants,
        'available_sizes': sorted(available_sizes, key=lambda x: x.id),
        'available_colors': sorted(available_colors, key=lambda x: x.name),
        'related_products': related_products,
    }
    
    return render(request, 'product_detail.html', context)


def api_inventory(request):
    """API endpoint for inventory data"""
    variants = ProductVariant.objects.select_related(
        'product', 'size', 'color', 'inventory'
    ).all()
    
    data = []
    for variant in variants:
        try:
            inv = variant.inventory
            data.append({
                'id': variant.id,
                'product': variant.product.name,
                'size': variant.size.name,
                'color': variant.color.name,
                'quantity': inv.quantity,
                'is_low_stock': inv.is_low_stock,
                'is_out_of_stock': inv.is_out_of_stock,
            })
        except Inventory.DoesNotExist:
            data.append({
                'id': variant.id,
                'product': variant.product.name,
                'size': variant.size.name,
                'color': variant.color.name,
                'quantity': 0,
                'is_low_stock': False,
                'is_out_of_stock': True,
            })
    
    return JsonResponse({'inventory': data})


# Helper functions

def decode_base64_image(base64_string):
    """Decode base64 image to numpy array"""
    # Remove data URL prefix if present
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    # Decode base64
    image_data = base64.b64decode(base64_string)
    
    # Convert to PIL Image
    pil_image = Image.open(BytesIO(image_data))
    
    # Convert to numpy array (RGB)
    image_array = np.array(pil_image)
    
    # Convert RGB to BGR for OpenCV
    if len(image_array.shape) == 3 and image_array.shape[2] == 3:
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    else:
        image_bgr = image_array
    
    return image_bgr
