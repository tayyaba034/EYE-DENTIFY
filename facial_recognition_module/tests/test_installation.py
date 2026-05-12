import sys
import os
from pathlib import Path

# Fix OpenMP runtime conflict
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_imports():
    modules = {
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'insightface': 'InsightFace',
        'onnxruntime': 'ONNX Runtime',
        'PIL': 'Pillow'
    }
    
    all_success = True
    
    for module, name in modules.items():
        try:
            __import__(module)
            print(f"✓ {name:20s} - OK")
        except ImportError as e:
            print(f"✗ {name:20s} - FAILED ({e})")
            all_success = False
    
    print()
    assert all_success


def test_opencv_version():
    """Test OpenCV version and webcam support."""
    print("=" * 60)
    print("Testing OpenCV")
    print("=" * 60)
    
    try:
        import cv2
        print(f"✓ OpenCV version: {cv2.__version__}")
        
        # Test webcam access
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("✓ Webcam access: OK")
            cap.release()
        else:
            print("⚠ Webcam access: FAILED (may not be available)")
        
        print()
    except Exception as e:
        print(f"✗ OpenCV test failed: {e}")
        print()
        raise


def test_insightface():
    """Test InsightFace functionality."""
    print("=" * 60)
    print("Testing InsightFace")
    print("=" * 60)
    
    try:
        from insightface.app import FaceAnalysis
        print("✓ InsightFace import: OK")
        
        print("  Note: Models will be downloaded on first use (~100MB)")
        print()
    except Exception as e:
        print(f"✗ InsightFace test failed: {e}")
        print()
        raise


def test_project_structure():
    """Test if all required files are present."""
    print("=" * 60)
    print("Testing Project Structure")
    print("=" * 60)
    
    required_files = [
        'entrypoint/train.py',
        'entrypoint/inference.py',
        'config/config.py',
        'src/pipelines/feature_eng_pipeline.py',
        'src/pipelines/inference_pipeline.py',
        'src/utils/utils.py',
        'src/utils/helpers.py',
        'requirements.txt', 
        'data/01-raw'
    ]
    
    all_present = True
    
    for file in required_files:
        if (PROJECT_ROOT / file).exists():
            print(f"✓ {file:40s} - Found")
        else:
            print(f"✗ {file:40s} - Missing")
            all_present = False
    
    print()
    assert all_present


def main():
    
    results = []
    
    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("OpenCV", test_opencv_version()))
    results.append(("InsightFace", test_insightface()))
    results.append(("Project Structure", test_project_structure()))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    
    if all(result[1] for result in results):
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Add reference image to: reference_images/person.jpg")
        print("2. Run the application: python main.py")
        print()
        return 0
    else:
        print("=" * 60)
        print("Some tests failed. Please check the errors above.")
        print("=" * 60)
        print()
        print("Troubleshooting:")
        print("1. Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        print("2. Check if you're in the correct directory")
        print("3. Ensure Python version is 3.8 or higher")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
