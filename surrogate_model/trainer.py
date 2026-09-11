import numpy as np
import pandas as pd
import joblib

from scipy.stats import spearmanr

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, r2_score

from feature_engineering import (
    build_clusters,
    build_relative_features
)


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

data = pd.read_csv(
    DATASET_PATH
)

nodes = pd.read_csv(
    NODES_PATH
)


# ============================================================
# Optional connected-only filtering
#
# If dataset.csv contains a "connected" column, only feasible
# samples are used.
#
# If your generator already guarantees that every row is
# connected, this block simply does nothing.
# ============================================================

if "connected" in data.columns:

    total_before = len(
        data
    )

    data = data[
        data["connected"].astype(int) == 1
    ].copy()

    print(
        "Connected samples:",
        len(data),
        "/",
        total_before
    )


# ============================================================
# Basic validation
# ============================================================

if RANGE_COLUMN not in data.columns:

    raise ValueError(
        f"Column '{RANGE_COLUMN}' "
        f"not found in dataset.csv"
    )


relay_counts = data[
    "n_relays"
].unique()


if len(relay_counts) != 1:

    raise ValueError(
        "RF currently expects a fixed number "
        "of relays. "
        f"Found: {relay_counts}"
    )


N_RELAYS = int(
    relay_counts[0]
)


cluster_counts = nodes[
    "n_clusters"
].unique()


if len(cluster_counts) != 1:

    raise ValueError(
        "RF currently expects a fixed number "
        "of clusters. "
        f"Found: {cluster_counts}"
    )


N_CLUSTERS = int(
    cluster_counts[0]
)


print(
    "Relays:",
    N_RELAYS
)

print(
    "Clusters:",
    N_CLUSTERS
)


# ============================================================
# Build cluster representation once per sensor scenario
# ============================================================

scenario_clusters = {}


for scenario_id, group in nodes.groupby(
    "scenario_id"
):

    n_clusters = int(
        group[
            "n_clusters"
        ].iloc[0]
    )


    node_positions = group[
        [
            "x",
            "y"
        ]
    ].to_numpy(
        dtype=float
    )


    scenario_clusters[
        scenario_id
    ] = build_clusters(
        node_positions,
        n_clusters
    )


# ============================================================
# Generate engineered feature rows
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


    # --------------------------------------------------------
    # Sink
    # --------------------------------------------------------

    sink = np.array(
        [
            row["sink_x"],
            row["sink_y"]
        ],
        dtype=float
    )


    # --------------------------------------------------------
    # Relay positions
    #
    # Keep original IDs here.
    # build_relative_features() removes identity dependence by
    # sorting RELATIONSHIPS, not relay objects.
    # --------------------------------------------------------

    relays = []


    for relay_idx in range(
        N_RELAYS
    ):

        relays.append(
            np.array(
                [
                    row[
                        f"relay_{relay_idx}_x"
                    ],

                    row[
                        f"relay_{relay_idx}_y"
                    ]
                ],
                dtype=float
            )
        )


    # --------------------------------------------------------
    # Feature engineering
    # --------------------------------------------------------

    features = build_relative_features(

        area_width=
            row["area_width"],

        area_height=
            row["area_height"],

        sink=
            sink,

        relays=
            relays,

        relay_power=
            row["relay_power"],

        relay_traffic=
            row["relay_traffic"],

        node_power=
            row["node_power"],

        node_traffic=
            row["node_traffic"],

        propagation=
            row["propagation"],

        packet_length=
            row["packet_length"],

        interval=
            row["interval"],

        simulated_range=
            row[RANGE_COLUMN],

        clusters=
            scenario_clusters[
                scenario_id
            ]
    )


    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    features[
        "scenario_id"
    ] = scenario_id


    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    features[
        "fitness"
    ] = row[
        "fitness"
    ]


    feature_rows.append(
        features
    )


# ============================================================
# Create engineered dataset
# ============================================================

feature_data = pd.DataFrame(
    feature_rows
)


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
    print(
        column
    )


# ============================================================
# X / y
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
# Validate engineered dataset
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
    X.to_numpy(
        dtype=float
    )
).any():

    raise ValueError(
        "Infinite values found in features"
    )


# ============================================================
# Grouped train/test split
#
# Entire WSN scenarios remain either in train or test.
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
print(
    "=============================="
)

print(
    "RF V2.1 RESULTS"
)

print(
    "=============================="
)

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
# High-fitness ranking
# ============================================================

top_25_threshold = y_test.quantile(
    0.75
)


top_25_mask = (
    y_test >=
    top_25_threshold
)


top_25_spearman, top_25_p = spearmanr(
    y_test[top_25_mask],
    predictions[top_25_mask]
)


top_10_threshold = y_test.quantile(
    0.90
)


top_10_mask = (
    y_test >=
    top_10_threshold
)


top_10_spearman, top_10_p = spearmanr(
    y_test[top_10_mask],
    predictions[top_10_mask]
)


print(
    "Top 25% Spearman:",
    top_25_spearman
)

print(
    "Top 25% p-value:",
    top_25_p
)

print(
    "Top 10% Spearman:",
    top_10_spearman
)

print(
    "Top 10% p-value:",
    top_10_p
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
print(
    "=============================="
)

print(
    "FEATURE IMPORTANCE"
)

print(
    "=============================="
)


print(
    importance.head(
        25
    ).to_string(
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
            RANGE_COLUMN,

        "feature_version":
            "v2.1_sorted_relationships"
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