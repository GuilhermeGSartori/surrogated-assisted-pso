import pandas as pd
import joblib

from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, r2_score


# ============================================================
# Load data
# ============================================================

data = pd.read_csv("../../surrogate_model/data/dataset.csv")
nodes = pd.read_csv("../../surrogate_model/data/nodes.csv")


# ============================================================
# Cluster each scenario
# ============================================================

scenario_cluster_features = []


for scenario_id, group in nodes.groupby("scenario_id"):

    n_clusters = int(group["n_clusters"].iloc[0])

    # Only X and Y are inputs to KMeans
    node_positions = group[["x", "y"]].to_numpy()

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    kmeans.fit(node_positions)

    centroids = kmeans.cluster_centers_


    # IMPORTANT:
    # Give centroids a deterministic order.
    # KMeans cluster IDs themselves have no fixed meaning.
    centroids = centroids[
        centroids[:, 0].argsort()
    ]


    # One row of features for this scenario
    features = {
        "scenario_id": scenario_id
    }


    for i, centroid in enumerate(centroids):

        features[f"centroid_{i}_x"] = centroid[0]
        features[f"centroid_{i}_y"] = centroid[1]


    scenario_cluster_features.append(features)


# ============================================================
# Convert scenario features to DataFrame
# ============================================================

clusters = pd.DataFrame(
    scenario_cluster_features
)


# ============================================================
# Attach cluster features to main dataset
# ============================================================

data = data.merge(
    clusters,
    on="scenario_id",
    how="left"
)


print(data.head())

## dar escolha também ao acordar o treinador... tipo RANDOM FOREST

groups = data["scenario_id"]

X = data.drop(
    columns=[
        "fitness",
        "scenario_id",
        "sample_id",
        "network_seed",
        "n_relays"
    ]
)

y = data["fitness"]


splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.2,
    random_state=42
)

train_idx, test_idx = next(
    splitter.split(X, y, groups=groups)
)

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]


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

joblib.dump(
    {
        "model": model,
        "features": X.columns.tolist()
    },
    "../../surrogate_model/data/rf_model.joblib"
)