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

print("Model loaded.")
print("Expected features:", len(feature_names))


# ============================================================
# Prepare RF features
# ============================================================

def prepare_features(message):

    # Packet format:
    #
    # RF_DATA*,NODE_X,NODE_Y,...,N_CLUSTERS
    #
    # Everything before "*," is already in RF feature format.
    # Everything after "*," must be clustered.

    if "*," not in message:
        raise ValueError("Packet does not contain '*,' separator")


    # ========================================================
    # Split packet
    # ========================================================

    feature_part, node_part = message.split("*,", 1)


    # ========================================================
    # Parse existing RF features
    # ========================================================

    features = [
        float(value)
        for value in feature_part.split(",")
    ]


    # ========================================================
    # Parse node information
    # ========================================================

    node_values = node_part.split(",")

    if len(node_values) < 3:
        raise ValueError("Invalid node section")


    # Last value is number of clusters
    n_clusters = int(node_values[-1])


    # Everything before that is:
    #
    # x0,y0,x1,y1,x2,y2,...
    #
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
    ).reshape(-1, 2)


    if n_clusters <= 0:
        raise ValueError(
            "n_clusters must be greater than zero"
        )

    if n_clusters > len(node_positions):
        raise ValueError(
            "n_clusters cannot be greater than number of nodes"
        )


    # ========================================================
    # KMeans
    #
    # MUST match trainer.py exactly
    # ========================================================

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    kmeans.fit(node_positions)

    centroids = kmeans.cluster_centers_


    # Same deterministic ordering used during training
    centroids = centroids[
        centroids[:, 0].argsort()
    ]


    # ========================================================
    # Append centroid features
    # ========================================================

    for centroid in centroids:

        features.append(
            centroid[0]
        )

        features.append(
            centroid[1]
        )


    # ========================================================
    # Verify against trained RF
    # ========================================================

    if len(features) != len(feature_names):

        raise ValueError(
            f"Feature count mismatch: "
            f"received {len(features)}, "
            f"model expects {len(feature_names)}"
        )


    # Using a DataFrame preserves the same column names/order
    # used during training.

    X = pd.DataFrame(
        [features],
        columns=feature_names
    )

    return X


# ============================================================
# Receive one complete packet
# ============================================================

def receive_packet(conn):

    buffer = ""

    while True:

        data = conn.recv(4096)

        if not data:
            break

        buffer += data.decode()

        # C++ terminates each packet with '\n'
        if "\n" in buffer:
            break


    if not buffer:
        return None


    # Only first complete packet
    message = buffer.split("\n", 1)[0]

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
        (HOST, PORT)
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

                message = receive_packet(conn)

                if not message:
                    continue


                # ============================================
                # Prepare features
                # ============================================

                X = prepare_features(
                    message
                )


                # ============================================
                # Predict fitness
                # ============================================

                prediction = model.predict(X)[0]


                print(
                    f"Prediction: {prediction}"
                )


                # ============================================
                # Return fitness to C++
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
