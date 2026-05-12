"""
Feature Engineering Pipeline
Extracts face embeddings from reference images and stores them.
"""

import os
import sys
import numpy as np
import cv2
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import (
    RAW_DATA_DIR,
    FEATURES_DIR,
    MODEL_NAME,
    MODEL_ROOT,
    DETECTION_THRESHOLD,
    INPUT_SIZE
)
from src.utils.helpers import get_image_files, preprocess_image
from insightface.app import FaceAnalysis


class FeatureExtractionPipeline:
    
    def __init__(self):
        """Initialize the feature extraction pipeline."""
        print("=" * 70)
        print("Feature Engineering Pipeline - Face Embedding Extraction")
        print("=" * 70)
        
        # Initialize InsightFace
        print("\n[1/3] Initializing InsightFace model...")
        self.app = FaceAnalysis(
            name=MODEL_NAME,
            root=MODEL_ROOT,
            providers=['CPUExecutionProvider']
        )
        self.app.prepare(
            ctx_id=0,
            det_thresh=DETECTION_THRESHOLD,
            det_size=INPUT_SIZE
        )
        print("✓ InsightFace model loaded")
        
        # Storage for embeddings
        self.embeddings = {}
        self.metadata = {}
    
    def extract_embedding_from_image(self, image_path: str) -> tuple:
        try:
            # Load image
            image = preprocess_image(image_path)
            
            # Detect faces
            faces = self.app.get(image)
            
            if len(faces) == 0:
                print(f"  ✗ No face detected in {os.path.basename(image_path)}")
                return None, None, False
            
            if len(faces) > 1:
                print(f"  ⚠ Multiple faces detected in {os.path.basename(image_path)}, using first face")
            
            # Extract embedding from first face
            face = faces[0]
            embedding = face.embedding
            bbox = face.bbox
            
            print(f"  ✓ Embedding extracted from {os.path.basename(image_path)}")
            print(f"    - Embedding shape: {embedding.shape}")
            print(f"    - Face bbox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")
            
            return embedding, bbox, True
            
        except Exception as e:
            print(f"  ✗ Error processing {os.path.basename(image_path)}: {e}")
            return None, None, False
    
    def process_reference_images(self):
        print(f"\n[2/3] Processing reference images from: {RAW_DATA_DIR}")
        
        # Get all image files
        image_files = get_image_files(RAW_DATA_DIR)
        
        if len(image_files) == 0:
            print(f"\n✗ No image files found in {RAW_DATA_DIR}")
            print("\nPlease add your reference images to:")
            print(f"  {RAW_DATA_DIR}")
            print("\nSupported formats: .jpg, .jpeg, .png, .bmp")
            return False
        
        print(f"\nFound {len(image_files)} image(s):")
        for img_file in image_files:
            print(f"  - {os.path.basename(img_file)}")
        
        print("\nExtracting embeddings...")
        
        # Process each image
        success_count = 0
        for image_path in image_files:
            person_name = os.path.splitext(os.path.basename(image_path))[0]
            
            embedding, bbox, success = self.extract_embedding_from_image(image_path)
            
            if success:
                self.embeddings[person_name] = embedding
                self.metadata[person_name] = {
                    'image_path': image_path,
                    'bbox': bbox.tolist(),
                    'embedding_shape': embedding.shape
                }
                success_count += 1
        
        print(f"\n✓ Successfully processed {success_count}/{len(image_files)} images")
        
        return success_count > 0
    
    def save_features(self):
        print(f"\n[3/3] Saving features to: {FEATURES_DIR}")
        
        # Create features directory
        os.makedirs(FEATURES_DIR, exist_ok=True)
        
        # Save embeddings
        embeddings_file = os.path.join(FEATURES_DIR, 'reference_embeddings.npz')
        np.savez(embeddings_file, **self.embeddings)
        print(f"✓ Embeddings saved to: {embeddings_file}")
        
        # Save metadata
        import json
        metadata_file = os.path.join(FEATURES_DIR, 'embeddings_metadata.json')
        
        # Convert numpy arrays to lists for JSON serialization
        serializable_metadata = {}
        for name, meta in self.metadata.items():
            serializable_metadata[name] = {
                'image_path': meta['image_path'],
                'bbox': meta['bbox'],
                'embedding_shape': list(meta['embedding_shape'])
            }
        
        with open(metadata_file, 'w') as f:
            json.dump(serializable_metadata, f, indent=2)
        print(f"✓ Metadata saved to: {metadata_file}")
        
        return True
    
    def run(self):
        # Step 1: Process images
        if not self.process_reference_images():
            return False
        
        # Step 2: Save features
        if not self.save_features():
            return False
        
        print("\n" + "=" * 70)
        print("Feature extraction completed successfully!")
        print("=" * 70)
        print(f"\nExtracted {len(self.embeddings)} face embedding(s):")
        for name in self.embeddings.keys():
            print(f"  - {name}")
        
        print("\nYou can now run the inference pipeline:")
        print("  python entrypoint/inference.py")
        print("=" * 70)
        
        return True


def main():
    pipeline = FeatureExtractionPipeline()
    success = pipeline.run()
    
    if not success:
        print("\n" + "=" * 70)
        print("Feature extraction failed. Please check the errors above.")
        print("=" * 70)
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
