"""Load pre-trained model and make predictions."""
import tensorflow as tf
import numpy as np

def load_trained_model(path):
    """Load a pre-trained model."""
    # Consumer keyword: load_model
    model = tf.keras.models.load_model(path)
    return model

def make_predictions(model, data):
    """Make predictions using the model."""
    # Consumer keyword: predict
    predictions = model.predict(data)
    return predictions

def run_inference():
    """Run inference on test data."""
    model = load_trained_model('pretrained_model.h5')
    
    # Generate test data
    test_data = np.random.random((10, 20))
    
    # Make predictions
    results = make_predictions(model, test_data)
    
    print(f"Predictions: {results.shape}")
    return results

if __name__ == "__main__":
    run_inference()
