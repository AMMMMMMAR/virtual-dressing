# Intelligent In-Store Virtual Fitting System

An AI-powered virtual fitting system for men's and women's clothing stores. The system uses computer vision to estimate body measurements and skin tone, then provides intelligent clothing recommendations based on available inventory.

## Features

- **Real-Time Visual Guidance**: Interactive camera interface with body outline overlay and live feedback to ensure perfect pose.
- **AI Body Measurement**: Uses MediaPipe Pose (New Task API) to estimate height, shoulder width, chest, and waist measurements with high accuracy.
- **Skin Tone Analysis**: Analyzes skin tone using MediaPipe Face Detection to recommend suitable colors.
- **Intelligent Recommendations**: Suggests appropriate size, fit, and products based on measurements and inventory.
- **3D Avatar Visualization**: Displays a parametric 3D avatar using Three.js to visualize the fit.
- **Online Store**: Browse products with filtering and search capabilities.
- **Inventory Management**: Real-time stock tracking with low stock alerts.
- **Privacy-First**: Images are processed in memory and never stored.

## Technology Stack

- **Backend**: Django 4.2+ with SQLite database
- **Frontend**: Django Templates with Tailwind CSS
- **AI/CV**: MediaPipe (Pose + Face Detection), OpenCV, NumPy
- **3D Graphics**: Three.js
- **Python**: 3.9+

## Installation

### Prerequisites

- Python 3.9 or higher
- Webcam (for body scanning)
- Modern web browser (Chrome, Firefox, or Edge)
- Internet connection (for initial model download)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/AMMMMMMAR/AI-dressing.git
   cd AI-dressing
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\Activate.ps1
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download MediaPipe Model**
   The system requires the `pose_landmarker.task` model file in the project root.
   ```bash
   # Using curl (Windows/Linux/Mac):
   curl -L -o pose_landmarker.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task
   
   # Or using Python:
   python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task', 'pose_landmarker.task')"
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Populate initial data**
   ```bash
   python manage.py populate_data
   ```

7. **Create a superuser (for admin access)**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Main application: http://localhost:8000/
   - Admin panel: http://localhost:8000/admin/

## Usage Guide

### For Customers

1. **Virtual Fitting**:
   - Click "Try Virtual Fitting" from the homepage or navigation.
   - Allow camera access when prompted.
   - **Real-Time Guidance**: Stand back until your body fits the outline.
   - Wait for the status indicator to turn **Green** ("Perfect! Hold still...").
   - Click "Start Scanning" or "Capture Front View".
   - View your measurements, recommended size/fit, and product suggestions.

2. **Browse Store**:
   - Navigate to "Store" to browse all products.
   - Use filters to narrow down by category, gender, or search.
   - Click "Try Virtual Fitting" on product pages to get personalized recommendations.

### For Store Employees

1. **Inventory Management**:
   - Navigate to "Inventory" to view stock levels.
   - Low stock items are highlighted in yellow.
   - Out of stock items are highlighted in red.
   - Click "Manage Inventory in Admin Panel" for detailed management.

2. **Admin Panel**:
   - Access at http://localhost:8000/admin/
   - Login with superuser credentials.
   - Manage products, sizes, colors, variants, and inventory.
   - View scan history and recommendations.

## System Architecture

### AI/CV Pipeline

1. **Real-Time Pose Analysis**:
   - Analyzes video frames at 2FPS (`/analyze-frame/` endpoint).
   - Checks for feet visibility, head position, and distance.
   - Provides immediate feedback to the user.

2. **Body Measurement Estimation**:
   - Uses MediaPipe Pose (Heavy model) to detect 33 body landmarks.
   - Calculates measurements based on landmark distances and calibrated pixel-to-cm ratios.
   - Estimates: Height, Shoulder Width, Chest, Waist.

3. **Skin Tone Analysis**:
   - Detects face region and analyzes color in YCrCb space.
   - Classifies skin tone (Light/Medium/Dark) for color coordination.

4. **Recommendation Engine**:
   - Maps measurements to industry-standard size charts.
   - Recommends "Slim", "Regular", or "Oversize" fit based on body proportions.
   - Suggests complementary clothing colors based on skin tone.

### Database Models

- **Size**: Measurement ranges for sizes (S, M, L, etc.).
- **Color**: Color hex codes and metadata.
- **Product**: Catalog items with category and fit type.
- **ProductVariant**: Specific SKUs (Product + Size + Color).
- **Inventory**: Stock count for each variant.
- **BodyScan**: Session data (measurements only, no images stored).

## API Endpoints

- `POST /analyze-frame/`: Real-time pose analysis (JSON).
- `POST /process-scan/`: Final measurement processing.
- `GET /scan/`: Main camera interface.
- `GET /store/`: Product catalog.
- `GET /api/inventory/`: Inventory status API.

## Troubleshooting

### Camera Issues
- Ensure you have granted camera permissions in your browser.
- If the screen says "Camera access denied", check your browser settings (site settings) and allow camera access.
- Ensure no other app (Zoom, Teams) is using the camera.

### "No person detected"
- Make sure you are standing 2-3 meters away.
- Ensure there is sufficient lighting.
- The system requires your full body (head to feet) to be visible.

### 500 Server Error
- Check the terminal output for python errors.
- Ensure `pose_landmarker.task` is present in the project folder.

## License

This is an academic prototype for demonstration purposes.

