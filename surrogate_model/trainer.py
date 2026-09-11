import numpy as np
import pandas as pd
import joblib

from scipy.stats import spearmanr

from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, r2_score


# ============================================================
# Configuration
# ============================================================

DATASET_PATH = "../../surrogate_model/data/dataset.csv"
NODES_PATH = "../../surrogate_model/data/nodes.csv"

MODEL_PATH = "../../surrogate_model/data/rf_model.joblib"
FEATURES_PATH = "../../surrogate_model/data/engineered_features.csv"

RANGE_COLUMN = "simulated_range"


# ============================================================
# Load data
# ============================================================

data = pd.read_csv(DATASET_PATH)
nodes = pd.read_csv(NODES_PATH)


# ============================================================
# Basic validation
# ============================================================

if RANGE_COLUMN not in data.columns:
    raise ValueError(
        f"Column '{RANGE_COLUMN}' not found in dataset.csv"
    )


# Fixed relay count for this RF
relay_counts = data["n_relays"].unique()

if len(relay_counts) != 1:
    raise ValueError(
        "RF v2 currently expects a fixed number of relays. "
        f"Found: {relay_counts}"
    )

N_RELAYS = int(relay_counts[0])


# Fixed cluster count for this RF
cluster_counts = nodes["n_clusters"].unique()

if len(cluster_counts) != 1:
    raise ValueError(
        "RF v2 currently expects a fixed number of clusters. "
        f"Found: {cluster_counts}"
    )

N_CLUSTERS = int(cluster_counts[0])


print("Relays:", N_RELAYS)
print("Clusters:", N_CLUSTERS)


# ============================================================
# Utility
# ============================================================

def distance(a, b):
    return np.linalg.norm(a - b)


# ============================================================
# Build cluster representation for each scenario
# ============================================================

def build_scenario_clusters(nodes_df):

    scenario_clusters = {}

    for scenario_id, group in nodes_df.groupby("scenario_id"):

        n_clusters = int(
            group["n_clusters"].iloc[0]
        )

        node_positions = group[
            ["x", "y"]
        ].to_numpy(dtype=float)


        # ----------------------------------------------------
        # KMeans
        # ----------------------------------------------------

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10
        )

        labels = kmeans.fit_predict(
            node_positions
        )

        centroids = kmeans.cluster_centers_


        # ----------------------------------------------------
        # Describe each cluster
        #
        # IMPORTANT:
        # NO CANONICAL REORDERING.
        #
        # Cluster 0 stays KMeans cluster 0,
        # cluster 1 stays KMeans cluster 1, etc.
        # ----------------------------------------------------

        clusters = []

        for cluster_id in range(n_clusters):

            members = node_positions[
                labels == cluster_id
            ]

            centroid = centroids[
                cluster_id
            ]

            distances_to_centroid = (
                np.linalg.norm(
                    members - centroid,
                    axis=1
                )
            )


            clusters.append({

                "centroid":
                    centroid,

                "size":
                    len(members),

                "mean_radius":
                    distances_to_centroid.mean(),

                "max_radius":
                    distances_to_centroid.max(),

                "std_radius":
                    distances_to_centroid.std()
            })


        scenario_clusters[
            scenario_id
        ] = clusters


    return scenario_clusters


scenario_clusters = build_scenario_clusters(
    nodes
)


# ============================================================
# Build RF v2 features
# ============================================================

def build_relative_features(
    row,
    clusters
):

    features = {}


    # ========================================================
    # Scenario geometry
    # ========================================================

    width = float(
        row["area_width"]
    )

    height = float(
        row["area_height"]
    )


    if width <= 0.0 or height <= 0.0:
        raise ValueError(
            "Area dimensions must be greater than zero"
        )


    area = width * height

    area_diagonal = np.sqrt(
        width ** 2 +
        height ** 2
    )


    sink = np.array(
        [
            row["sink_x"],
            row["sink_y"]
        ],
        dtype=float
    )


    # ========================================================
    # Relay positions
    #
    # IMPORTANT:
    # NO CANONICAL ORDERING.
    #
    # relay_0 stays relay_0
    # relay_1 stays relay_1
    # etc.
    # ========================================================

    relays = []

    for i in range(N_RELAYS):

        relay = np.array(
            [
                row[f"relay_{i}_x"],
                row[f"relay_{i}_y"]
            ],
            dtype=float
        )

        relays.append(
            relay
        )


    # ========================================================
    # Clusters
    #
    # Also preserve their original KMeans order.
    # No sorting by sink distance, X coordinate, radius, etc.
    # ========================================================

    ordered_clusters = clusters


    # ========================================================
    # Simulated relay communication range
    # ========================================================

    simulated_range = float(
        row[RANGE_COLUMN]
    )


    if simulated_range <= 0.0:
        raise ValueError(
            "simulated_range must be greater than zero"
        )


    # ========================================================
    # General scenario features
    # ========================================================

    features["area"] = area

    features["aspect_ratio"] = (
        width / height
    )


    total_nodes = sum(
        cluster["size"]
        for cluster in ordered_clusters
    )


    features["node_density"] = (
        total_nodes / area
    )


    # ========================================================
    # Network configuration
    # ========================================================

    features["relay_power"] = (
        row["relay_power"]
    )

    features["node_power"] = (
        row["node_power"]
    )

    features["relay_traffic"] = (
        row["relay_traffic"]
    )

    features["node_traffic"] = (
        row["node_traffic"]
    )

    features["propagation"] = (
        row["propagation"]
    )

    features["packet_length"] = (
        row["packet_length"]
    )

    features["interval"] = (
        row["interval"]
    )


    # Calibrated relay-to-relay communication range
    features["simulated_range"] = (
        simulated_range
    )


    # ========================================================
    # Relay <-> Relay
    #
    # relay_i and relay_j retain their ORIGINAL identities.
    #
    # Normalized by calibrated relay-to-relay range.
    # ========================================================

    for i in range(N_RELAYS):

        for j in range(
            i + 1,
            N_RELAYS
        ):

            d = distance(
                relays[i],
                relays[j]
            )


            features[
                f"relay_{i}_{j}_relative_distance"
            ] = (
                d /
                simulated_range
            )


    # ========================================================
    # Relay <-> Sink
    #
    # Normalized by deployment-area diagonal.
    # ========================================================

    for i, relay in enumerate(
        relays
    ):

        d = distance(
            relay,
            sink
        )


        features[
            f"relay_{i}_sink_relative_distance"
        ] = (
            d /
            area_diagonal
        )


    # ========================================================
    # Cluster features
    # ========================================================

    for cluster_idx, cluster in enumerate(
        ordered_clusters
    ):

        centroid = cluster[
            "centroid"
        ]


        # ----------------------------------------------------
        # Relative cluster population
        # ----------------------------------------------------

        features[
            f"cluster_{cluster_idx}_population"
        ] = (
            cluster["size"] /
            total_nodes
        )


        # ----------------------------------------------------
        # Cluster spatial spread
        # ----------------------------------------------------

        features[
            f"cluster_{cluster_idx}_mean_radius"
        ] = (
            cluster["mean_radius"] /
            area_diagonal
        )


        features[
            f"cluster_{cluster_idx}_max_radius"
        ] = (
            cluster["max_radius"] /
            area_diagonal
        )


        features[
            f"cluster_{cluster_idx}_std_radius"
        ] = (
            cluster["std_radius"] /
            area_diagonal
        )


        # ----------------------------------------------------
        # Cluster <-> Sink
        # ----------------------------------------------------

        d_sink = distance(
            centroid,
            sink
        )


        features[
            f"cluster_{cluster_idx}_sink_relative_distance"
        ] = (
            d_sink /
            area_diagonal
        )


        # ----------------------------------------------------
        # Cluster <-> Relay
        #
        # Again, relay indices stay fixed.
        # ----------------------------------------------------

        for relay_idx, relay in enumerate(
            relays
        ):

            d_relay = distance(
                centroid,
                relay
            )


            features[
                f"cluster_{cluster_idx}_relay_{relay_idx}_relative_distance"
            ] = (
                d_relay /
                area_diagonal
            )


    return features


# ============================================================
# Generate engineered dataset
# ============================================================

feature_rows = []


for _, row in data.iterrows():

    scenario_id = row[
        "scenario_id"
    ]


    if scenario_id not in scenario_clusters:
        raise ValueError(
            f"No node information found "
            f"for scenario {scenario_id}"
        )


    features = build_relative_features(
        row,
        scenario_clusters[
            scenario_id
        ]
    )


    # Metadata used for grouped splitting
    features[
        "scenario_id"
    ] = scenario_id


    # Target
    features[
        "fitness"
    ] = row["fitness"]


    feature_rows.append(
        features
    )


feature_data = pd.DataFrame(
    feature_rows
)


# ============================================================
# Save engineered dataset
# ============================================================

feature_data.to_csv(
    FEATURES_PATH,
    index=False
)


print()
print(
    "Engineered dataset shape:",
    feature_data.shape
)

print()
print(
    "Engineered features:"
)

for column in feature_data.columns:
    print(column)


# ============================================================
# Prepare X / y
# ============================================================

groups = feature_data[
    "scenario_id"
]


X = feature_data.drop(
    columns=[
        "scenario_id",
        "fitness"
    ]
)


y = feature_data[
    "fitness"
]


# ============================================================
# Check for bad feature values
# ============================================================

if X.isnull().any().any():

    bad_columns = X.columns[
        X.isnull().any()
    ].tolist()

    raise ValueError(
        f"NaN values found in features: "
        f"{bad_columns}"
    )


if np.isinf(
    X.to_numpy(dtype=float)
).any():

    raise ValueError(
        "Infinite values found in features"
    )


# ============================================================
# Grouped train/test split
#
# Entire scenarios stay either in training or testing.
# ============================================================

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.2,
    random_state=42
)


train_idx, test_idx = next(
    splitter.split(
        X,
        y,
        groups=groups
    )
)


X_train = X.iloc[
    train_idx
]

X_test = X.iloc[
    test_idx
]

y_train = y.iloc[
    train_idx
]

y_test = y.iloc[
    test_idx
]


print()
print(
    "Training rows:",
    len(X_train)
)

print(
    "Testing rows:",
    len(X_test)
)

print(
    "Training scenarios:",
    groups.iloc[
        train_idx
    ].nunique()
)

print(
    "Testing scenarios:",
    groups.iloc[
        test_idx
    ].nunique()
)


# ============================================================
# Random Forest
# ============================================================

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# Train
# ============================================================

model.fit(
    X_train,
    y_train
)


# ============================================================
# Predict
# ============================================================

predictions = model.predict(
    X_test
)


# ============================================================
# Metrics
# ============================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

r2 = r2_score(
    y_test,
    predictions
)

spearman, spearman_p = spearmanr(
    y_test,
    predictions
)


print()
print("==============================")
print("RF V2 RESULTS")
print("==============================")

print(
    "MAE:",
    mae
)

print(
    "R²:",
    r2
)

print(
    "Spearman:",
    spearman
)

print(
    "Spearman p-value:",
    spearman_p
)


# ============================================================
# High-fitness ranking metrics
#
# Useful because PSO cares especially about ranking the
# best candidate solutions correctly.
# ============================================================

top_25_threshold = y_test.quantile(
    0.75
)

top_25_mask = (
    y_test >= top_25_threshold
)

top_25_spearman, _ = spearmanr(
    y_test[top_25_mask],
    predictions[top_25_mask]
)


top_10_threshold = y_test.quantile(
    0.90
)

top_10_mask = (
    y_test >= top_10_threshold
)

top_10_spearman, _ = spearmanr(
    y_test[top_10_mask],
    predictions[top_10_mask]
)


print(
    "Top 25% Spearman:",
    top_25_spearman
)

print(
    "Top 10% Spearman:",
    top_10_spearman
)


# ============================================================
# Feature importance
# ============================================================

importance = pd.DataFrame({

    "feature":
        X.columns,

    "importance":
        model.feature_importances_
})


importance = importance.sort_values(
    "importance",
    ascending=False
)


print()
print("==============================")
print("FEATURE IMPORTANCE")
print("==============================")

print(
    importance.head(20).to_string(
        index=False
    )
)


# ============================================================
# Save model
# ============================================================

joblib.dump(
    {
        "model":
            model,

        "features":
            X.columns.tolist(),

        "n_relays":
            N_RELAYS,

        "n_clusters":
            N_CLUSTERS,

        "range_column":
            RANGE_COLUMN
    },
    MODEL_PATH
)


print()
print(
    "Model saved to:",
    MODEL_PATH
)

print(
    "Feature count:",
    len(X.columns)
)