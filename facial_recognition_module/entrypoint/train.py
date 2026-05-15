#!/usr/bin/env python3
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipelines.feature_eng_pipeline import FeatureExtractionPipeline




def main():
 
    # Create and run pipeline
    pipeline = FeatureExtractionPipeline()
    success = pipeline.run()
    
    if not success:
        print("Feature extraction failed.")
        print("\nTroubleshooting:")
        print("1. Ensure reference images are in: data/01-raw/")
        print("2. Use clear, frontal-facing photos")
        print("3. Supported formats: .jpg, .jpeg, .png, .bmp")
        print("4. Each image should contain exactly one face")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
