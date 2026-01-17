"""Scikit-learn training script."""
from sklearn.ensemble import RandomForestClassifier
import numpy as np

X = np.random.random((100, 10))
y = np.random.randint(0, 2, 100)

clf = RandomForestClassifier()

# Producer keyword: fit
clf.fit(X, y)

print(f"Training accuracy: {clf.score(X, y)}")
