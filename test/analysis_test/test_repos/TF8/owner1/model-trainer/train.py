"""Train a neural network model."""
import tensorflow as tf
from tensorflow import keras
import numpy as np

def build_model():
    """Build a simple neural network."""
    model = keras.Sequential([
        keras.layers.Dense(128, activation='relu', input_shape=(20,)),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(10, activation='softmax')
    ])
    
    # Producer keyword: compile
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def train():
    """Train the model."""
    model = build_model()
    
    # Generate dummy training data
    X_train = np.random.random((1000, 20))
    y_train = np.random.randint(0, 10, (1000, 10))
    
    # Producer keyword: fit
    model.fit(X_train, y_train, epochs=5, batch_size=32)
    
    # Save trained model
    model.save('trained_model.h5')
    print("Training complete!")

if __name__ == "__main__":
    train()
