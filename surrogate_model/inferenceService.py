import socket
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.cluster import KMeans


# ============================================================
# Configuration
# ============================================================

print("Starting!")

HOST = "127.0.0.1"
PORT = 8080

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "data/rf_model.joblib"


# ============================================================
# Load model
# ============================================================

saved = joblib.load(MODEL_PATH)

model = saved["model"]
feature_names = saved["features"]

N_RELAYS = saved["n_relays"]
N_CLUSTERS = saved["n_clusters"]

print("Model loaded.")
print("Expected features:", len(feature_names))
print("Expected relays:", N_RELAYS)
print("Expected clusters:", N_CLUSTERS)


# ============================================================
# Utility
# ============================================================

def distance(a, b):
    return np.linalg.norm(a - b)


# ============================================================
# Build cluster representation
#
# MUST match trainer.py exactly.
#
# IMPORTANT:
# No canonical cluster ordering.
# KMeans cluster IDs are preserved exactly as generated.
# ============================================================

def build_clusters(
    node_positions,
    n_clusters
):

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    labels = kmeans.fit_predict(
        node_positions
    )

    centroids = kmeans.cluster_centers_

    clusters = []

    for cluster_id in range(
        n_clusters
    ):

        members = node_positions[
            labels == cluster_id
        ]

        centroid = centroids[
            cluster_id
        ]

        distances_to_centroid = np.linalg.norm(
            members - centroid,
            axis=1
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

    return clusters


# ============================================================
# Build engineered RF features
#
# MUST match trainer.py exactly.
#
# IMPORTANT:
# No canonical relay ordering.
# No canonical cluster ordering.
# ============================================================

def build_relative_features(
    area_width,
    area_height,
    sink,
    relays,
    relay_power,
    relay_traffic,
    node_power,
    node_traffic,
    propagation,
    packet_length,
    interval,
    simulated_range,
    clusters
):

    features = {}


    # ========================================================
    # Scenario geometry
    # ========================================================

    width = float(
        area_width
    )

    height = float(
        area_height
    )


    if width <= 0.0 or height <= 0.0:

        raise ValueError(
            "Area dimensions must be greater than zero"
        )


    area = (
        width *
        height
    )


    area_diagonal = np.sqrt(
        width ** 2 +
        height ** 2
    )


    # ========================================================
    # IMPORTANT:
    #
    # DO NOT reorder relays.
    #
    # relays[0] remains relay_0 from C++
    # relays[1] remains relay_1 from C++
    # etc.
    # ========================================================


    # ========================================================
    # IMPORTANT:
    #
    # DO NOT reorder clusters.
    #
    # cluster 0 remains KMeans cluster 0
    # cluster 1 remains KMeans cluster 1
    # etc.
    # ========================================================

    ordered_clusters = clusters


    # ========================================================
    # Validate simulated communication range
    # ========================================================

    simulated_range = float(
        simulated_range
    )


    if simulated_range <= 0.0:

        raise ValueError(
            "simulated_range must be greater than zero"
        )


    # ========================================================
    # General scenario features
    # ========================================================

    features["area"] = (
        area
    )


    features["aspect_ratio"] = (
        width /
        height
    )


    total_nodes = sum(
        cluster["size"]
        for cluster in ordered_clusters
    )


    features["node_density"] = (
        total_nodes /
        area
    )


    # ========================================================
    # Network features
    # ========================================================

    features["relay_power"] = (
        relay_power
    )

    features["node_power"] = (
        node_power
    )

    features["relay_traffic"] = (
        relay_traffic
    )

    features["node_traffic"] = (
        node_traffic
    )

    features["propagation"] = (
        propagation
    )

    features["packet_length"] = (
        packet_length
    )

    features["interval"] = (
        interval
    )

    features["simulated_range"] = (
        simulated_range
    )


    # ========================================================
    # Relay <-> Relay
    #
    # Relay identity stays fixed.
    #
    # Normalized using calibrated relay-to-relay range.
    # ========================================================

    for i in range(
        N_RELAYS
    ):

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
    # Normalized by area diagonal.
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
        # Relay IDs remain fixed.
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
# Prepare RF features from C++ packet
# ============================================================

def prepare_features(
    message
):

    # Packet:
    #
    # area_width,
    # area_height,
    # sink_x,
    # sink_y,
    #
    # relay_0_x,
    # relay_0_y,
    # ...
    #
    # relay_interface,
    # relay_frequency,
    # relay_bandwidth,
    # relay_bitrate,
    # relay_power,
    # relay_traffic,
    #
    # node_interface,
    # node_frequency,
    # node_bandwidth,
    # node_bitrate,
    # node_power,
    # node_traffic,
    #
    # propagation,
    # packet_length,
    # interval,
    # simulated_range
    #
    # *,
    #
    # node_0_x,
    # node_0_y,
    # ...
    # n_clusters


    if "*," not in message:

        raise ValueError(
            "Packet does not contain '*,' separator"
        )


    # ========================================================
    # Split packet
    # ========================================================

    raw_part, node_part = message.split(
        "*,",
        1
    )


    # ========================================================
    # Parse raw scenario information
    # ========================================================

    raw_values = [
        float(value)
        for value in raw_part.split(",")
    ]


    # 4:
    # width, height, sink x, sink y
    #
    # 2 * relays:
    # relay coordinates
    #
    # 6:
    # relay network configuration
    #
    # 6:
    # node network configuration
    #
    # 4:
    # propagation, packet length,
    # interval, simulated range

    expected_raw_values = (
        4 +
        (2 * N_RELAYS) +
        6 +
        6 +
        4
    )


    if len(raw_values) != expected_raw_values:

        raise ValueError(
            f"Raw packet field mismatch: "
            f"received {len(raw_values)}, "
            f"expected {expected_raw_values}"
        )


    index = 0


    # ========================================================
    # Area
    # ========================================================

    area_width = raw_values[
        index
    ]

    index += 1


    area_height = raw_values[
        index
    ]

    index += 1


    # ========================================================
    # Sink
    # ========================================================

    sink_x = raw_values[
        index
    ]

    index += 1


    sink_y = raw_values[
        index
    ]

    index += 1


    sink = np.array(
        [
            sink_x,
            sink_y
        ],
        dtype=float
    )


    # ========================================================
    # Relays
    #
    # IMPORTANT:
    # Preserve packet order exactly.
    # ========================================================

    relays = []


    for relay_idx in range(
        N_RELAYS
    ):

        relay_x = raw_values[
            index
        ]

        index += 1


        relay_y = raw_values[
            index
        ]

        index += 1


        relays.append(
            np.array(
                [
                    relay_x,
                    relay_y
                ],
                dtype=float
            )
        )


    # ========================================================
    # Relay network configuration
    # ========================================================

    # Currently still transmitted by C++,
    # but not used by RF v2.

    relay_interface = raw_values[
        index
    ]

    index += 1


    relay_frequency = raw_values[
        index
    ]

    index += 1


    relay_bandwidth = raw_values[
        index
    ]

    index += 1


    relay_bitrate = raw_values[
        index
    ]

    index += 1


    # Used by RF
    relay_power = raw_values[
        index
    ]

    index += 1


    relay_traffic = raw_values[
        index
    ]

    index += 1


    # ========================================================
    # Node network configuration
    # ========================================================

    # Currently still transmitted by C++,
    # but not used by RF v2.

    node_interface = raw_values[
        index
    ]

    index += 1


    node_frequency = raw_values[
        index
    ]

    index += 1


    node_bandwidth = raw_values[
        index
    ]

    index += 1


    node_bitrate = raw_values[
        index
    ]

    index += 1


    # Used by RF
    node_power = raw_values[
        index
    ]

    index += 1


    node_traffic = raw_values[
        index
    ]

    index += 1


    # ========================================================
    # Remaining network configuration
    # ========================================================

    propagation = raw_values[
        index
    ]

    index += 1


    packet_length = raw_values[
        index
    ]

    index += 1


    interval = raw_values[
        index
    ]

    index += 1


    simulated_range = raw_values[
        index
    ]

    index += 1


    # ========================================================
    # Parse sensor nodes
    # ========================================================

    node_values = node_part.split(
        ","
    )


    if len(node_values) < 3:

        raise ValueError(
            "Invalid node section"
        )


    # Last value = number of clusters
    n_clusters = int(
        node_values[-1]
    )


    raw_nodes = [
        float(value)
        for value in node_values[:-1]
    ]


    if len(raw_nodes) % 2 != 0:

        raise ValueError(
            "Node coordinates must contain X,Y pairs"
        )


    node_positions = np.array(
        raw_nodes,
        dtype=float
    ).reshape(
        -1,
        2
    )


    # ========================================================
    # Validate cluster configuration
    # ========================================================

    if n_clusters <= 0:

        raise ValueError(
            "n_clusters must be greater than zero"
        )


    if n_clusters > len(
        node_positions
    ):

        raise ValueError(
            "n_clusters cannot be greater than "
            "number of nodes"
        )


    if n_clusters != N_CLUSTERS:

        raise ValueError(
            f"Cluster count mismatch: "
            f"packet has {n_clusters}, "
            f"model expects {N_CLUSTERS}"
        )


    # ========================================================
    # KMeans + cluster statistics
    #
    # EXACTLY same preprocessing as trainer.
    #
    # NO sorting afterwards.
    # ========================================================

    clusters = build_clusters(
        node_positions,
        n_clusters
    )


    # ========================================================
    # Build engineered features
    # ========================================================

    features = build_relative_features(

        area_width=
            area_width,

        area_height=
            area_height,

        sink=
            sink,

        relays=
            relays,

        relay_power=
            relay_power,

        relay_traffic=
            relay_traffic,

        node_power=
            node_power,

        node_traffic=
            node_traffic,

        propagation=
            propagation,

        packet_length=
            packet_length,

        interval=
            interval,

        simulated_range=
            simulated_range,

        clusters=
            clusters
    )


    # ========================================================
    # Validate feature names
    # ========================================================

    generated_names = set(
        features.keys()
    )

    expected_names = set(
        feature_names
    )


    if generated_names != expected_names:

        missing = (
            expected_names -
            generated_names
        )

        extra = (
            generated_names -
            expected_names
        )


        raise ValueError(
            "Feature name mismatch. "
            f"Missing: {sorted(missing)} "
            f"Extra: {sorted(extra)}"
        )


    # ========================================================
    # Build RF input in EXACT training feature order
    # ========================================================

    ordered_values = [
        features[name]
        for name in feature_names
    ]


    X = pd.DataFrame(
        [
            ordered_values
        ],
        columns=feature_names
    )


    # ========================================================
    # Sanity checks
    # ========================================================

    if X.isnull().any().any():

        raise ValueError(
            "NaN found in generated RF features"
        )


    if np.isinf(
        X.to_numpy(
            dtype=float
        )
    ).any():

        raise ValueError(
            "Infinite value found in RF features"
        )


    return X


# ============================================================
# Receive one complete packet
# ============================================================

def receive_packet(
    conn
):

    buffer = ""


    while True:

        data = conn.recv(
            4096
        )


        if not data:
            break


        buffer += data.decode()


        # C++ terminates packet with newline
        if "\n" in buffer:
            break


    if not buffer:
        return None


    message = buffer.split(
        "\n",
        1
    )[0]


    return message.strip()


# ============================================================
# Server
# ============================================================

with socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
) as server:

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )


    server.bind(
        (
            HOST,
            PORT
        )
    )


    server.listen()


    print(
        f"RF inference service listening on "
        f"{HOST}:{PORT}"
    )


    while True:

        conn, addr = server.accept()


        with conn:

            try:

                message = receive_packet(
                    conn
                )


                if not message:
                    continue


                # ============================================
                # Prepare engineered features
                # ============================================

                X = prepare_features(
                    message
                )


                # ============================================
                # Predict
                # ============================================

                prediction = model.predict(
                    X
                )[0]


                print(
                    f"Prediction: {prediction}"
                )


                # ============================================
                # Return prediction to C++
                # ============================================

                response = (
                    f"{prediction}\n"
                )


                conn.sendall(
                    response.encode()
                )


            except Exception as e:

                print(
                    f"ERROR: {e}"
                )


                conn.sendall(
                    f"ERROR:{e}\n".encode()
                )