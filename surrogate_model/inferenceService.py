import socket
import joblib
import numpy as np
import pandas as pd

from pathlib import Path

from feature_engineering import (
    build_clusters,
    build_relative_features
)


# ============================================================
# Configuration
# ============================================================

print(
    "Starting!"
)

HOST = "127.0.0.1"
PORT = 8080

BASE_DIR = Path(
    __file__
).resolve().parent

MODEL_PATH = (
    BASE_DIR /
    "data/rf_model.joblib"
)


# ============================================================
# Load model
# ============================================================

saved = joblib.load(
    MODEL_PATH
)


model = saved[
    "model"
]

feature_names = saved[
    "features"
]

N_RELAYS = saved[
    "n_relays"
]

N_CLUSTERS = saved[
    "n_clusters"
]


print(
    "Model loaded."
)

print(
    "Feature version:",
    saved.get(
        "feature_version",
        "unknown"
    )
)

print(
    "Expected features:",
    len(feature_names)
)

print(
    "Expected relays:",
    N_RELAYS
)

print(
    "Expected clusters:",
    N_CLUSTERS
)


# ============================================================
# Prepare features from C++ packet
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
    # node_x,
    # node_y,
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
    # Raw scenario values
    # ========================================================

    raw_values = [
        float(value)
        for value in raw_part.split(",")
    ]


    expected_raw_values = (
        4 +
        (2 * N_RELAYS) +
        6 +
        6 +
        4
    )


    if len(
        raw_values
    ) != expected_raw_values:

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
    # Relay coordinates
    #
    # We preserve C++ order here.
    #
    # build_relative_features() itself removes dependence on
    # relay identity by sorting scalar relationships.
    # ========================================================

    relays = []


    for _ in range(
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

    # These four values are still present in the packet,
    # although RF v2.1 does not currently use them.

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
    # Node section
    # ========================================================

    node_values = node_part.split(
        ","
    )


    if len(
        node_values
    ) < 3:

        raise ValueError(
            "Invalid node section"
        )


    n_clusters = int(
        float(
            node_values[-1]
        )
    )


    raw_nodes = [
        float(value)
        for value in node_values[:-1]
    ]


    if len(
        raw_nodes
    ) % 2 != 0:

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
    # Validate
    # ========================================================

    if n_clusters <= 0:

        raise ValueError(
            "n_clusters must be greater than zero"
        )


    if n_clusters > len(
        node_positions
    ):

        raise ValueError(
            "n_clusters cannot be greater "
            "than number of nodes"
        )


    if n_clusters != N_CLUSTERS:

        raise ValueError(
            f"Cluster count mismatch: "
            f"packet has {n_clusters}, "
            f"model expects {N_CLUSTERS}"
        )


    # ========================================================
    # Cluster preprocessing
    #
    # EXACT same function used by trainer.py.
    # ========================================================

    clusters = build_clusters(
        node_positions,
        n_clusters
    )


    # ========================================================
    # Feature engineering
    #
    # EXACT same function used by trainer.py.
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
    # Exact trained feature order
    # ========================================================

    ordered_values = [
        features[
            name
        ]
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
                # Engineer exact same RF features as training
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
                # Send result
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