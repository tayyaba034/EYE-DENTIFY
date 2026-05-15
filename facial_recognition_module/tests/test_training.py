import sys
import os
import pytest
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.helpers import (
    cosine_similarity,
    euclidean_distance,
    similarity_to_percentage,
    validate_reference_image
)


class TestSimilarityMetrics:
    """Test similarity computation functions."""
    
    def test_cosine_similarity_identical(self):
        """Test cosine similarity for identical vectors."""
        embedding1 = np.array([1.0, 2.0, 3.0, 4.0])
        embedding2 = np.array([1.0, 2.0, 3.0, 4.0])
        
        similarity = cosine_similarity(embedding1, embedding2)
        
        assert abs(similarity - 1.0) < 1e-6, "Identical vectors should have similarity ~1.0"
    
    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity for orthogonal vectors."""
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        similarity = cosine_similarity(embedding1, embedding2)
        
        assert abs(similarity - 0.0) < 1e-6, "Orthogonal vectors should have similarity ~0.0"
    
    def test_euclidean_distance_identical(self):
        """Test Euclidean distance for identical vectors."""
        embedding1 = np.array([1.0, 2.0, 3.0, 4.0])
        embedding2 = np.array([1.0, 2.0, 3.0, 4.0])
        
        distance = euclidean_distance(embedding1, embedding2)
        
        assert abs(distance - 0.0) < 1e-6, "Identical vectors should have distance 0.0"
    
    def test_similarity_to_percentage(self):
        """Test conversion from similarity to percentage."""
        # Test various similarity values
        assert abs(similarity_to_percentage(1.0) - 100.0) < 1e-6
        assert abs(similarity_to_percentage(0.0) - 50.0) < 1e-6
        assert abs(similarity_to_percentage(-1.0) - 0.0) < 1e-6
        assert abs(similarity_to_percentage(0.5) - 75.0) < 1e-6


class TestValidation:
    """Test validation functions."""
    
    def test_validate_nonexistent_image(self):
        """Test validation of non-existent image."""
        result = validate_reference_image("/nonexistent/path/image.jpg")
        assert result is False, "Non-existent image should return False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
