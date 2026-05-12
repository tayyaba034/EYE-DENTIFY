#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipelines.inference_pipeline import InferencePipeline


def main():
    
    # Create and initialize pipeline
    pipeline = InferencePipeline()
    
    if not pipeline.initialize():
        print("Initialization failed.")
        print("\nTroubleshooting:")
        print("1. Run feature extraction first: python entrypoint/train.py")
        print("2. Ensure webcam is connected and accessible")
        print("3. Close other applications using the webcam")
        print("4. Check that reference embeddings exist in: data/03-features/")
        sys.exit(1)
    
    # Run inference
    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        pipeline.cleanup()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        pipeline.cleanup()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
