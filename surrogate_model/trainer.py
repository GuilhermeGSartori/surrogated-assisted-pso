import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


# Load dataset
data = pd.read_csv("dataset.csv")

# baseado nos nodos do dataset, numero de clusters... fazer clusters

k = 2

kmeans = KMeans(
    n_clusters=k,
    random_state=42,
    n_init=10
)

labels = kmeans.fit_predict(nodes)

centroids = kmeans.cluster_centers_

print("Labels:")
print(labels)

print("Centroids:")
print(centroids)


# Everything except fitness is input
X = data.drop(columns=["fitness"])

# Fitness is what we want to predict
y = data["fitness"]


# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# Create Random Forest
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)


# Train
model.fit(X_train, y_train)


# Test
predictions = model.predict(X_test)


print("MAE:", mean_absolute_error(y_test, predictions))
print("R²:", r2_score(y_test, predictions))