import numpy as np
from sklearn.cluster import KMeans
# ============================================================
# Utility
# ============================================================
def distance(a, b):
    return np.linalg.norm(a - b)
# ============================================================
# Build cluster representation
# ============================================================
def build_clusters(
    node_positions,
    n_clusters
):
    """
    Run KMeans and describe each resulting sensor cluster.
    The clusters are NOT ordered here.
    Cluster ordering is performed later relative to the sink,
    because that gives them a consistent physical meaning.
    """
    if n_clusters <= 0:
        raise ValueError(
            "n_clusters must be greater than zero"
        )
    if n_clusters > len(node_positions):
        raise ValueError(
            "n_clusters cannot be greater than number of nodes"
        )
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
            # Needed for node-level coverage features.
            "members":
                members.copy(),
            "mean_radius":
                distances_to_centroid.mean(),
            "max_radius":
                distances_to_centroid.max(),
            "std_radius":
                distances_to_centroid.std()
        })
    return clusters
# ============================================================
# Order clusters relative to sink
# ============================================================
def order_clusters(
    clusters,
    sink
):
    """
    Give clusters a deterministic physical meaning:
        cluster_0 = closest cluster to sink
        cluster_1 = second closest
        ...
    This is safe for PSO because sensor nodes and the sink do
    not move while relay positions are being optimized.
    """
    ordered = []
    for cluster in clusters:
        cluster_copy = cluster.copy()
        cluster_copy[
            "sink_distance"
        ] = distance(
            cluster["centroid"],
            sink
        )
        ordered.append(
            cluster_copy
        )
    ordered.sort(
        key=lambda cluster: (
            cluster["sink_distance"],
            cluster["mean_radius"],
            cluster["size"]
        )
    )
    return ordered
# ============================================================
# Build RF engineered features
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
    clusters,
    node_to_relay_range=None
):
    """
    Build RF v2.1 features.
    IMPORTANT:
    Relays are NEVER reordered.
    Instead, permutation invariance is obtained by sorting
    scalar relationship values:
        - relay <-> relay distances
        - relay <-> sink distances
        - cluster <-> relay distances
    This avoids arbitrary relay IDs while also avoiding
    dynamic identity swaps during PSO.

    node_to_relay_range is the calibrated range for transmissions
    FROM a sensor TO a relay (not the relay-to-relay range).
    It is required for the additional geometric coverage features.
    """
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
    if simulated_range <= 0.0:
        raise ValueError(
            "simulated_range must be greater than zero"
        )

    # The range of the sensor -> relay link depends on NODE power.
    # Never silently reuse relay-to-relay simulated_range here.
    if node_to_relay_range is None:
        raise ValueError(
            "node_to_relay_range is required for coverage features. "
            "Pass the calibrated sensor-to-relay range in meters."
        )

    node_to_relay_range = float(node_to_relay_range)
    if not np.isfinite(node_to_relay_range) or node_to_relay_range <= 0.0:
        raise ValueError(
            "node_to_relay_range must be finite and greater than zero"
        )

    relay_positions = np.asarray(relays, dtype=float)
    if (relay_positions.ndim != 2 or relay_positions.shape[1] != 2
            or len(relay_positions) == 0
            or not np.isfinite(relay_positions).all()):
        raise ValueError("relays must be a nonempty array of finite x,y positions")

    # ========================================================
    # Canonical CLUSTER ordering
    #
    # We are NOT canonicalizing relays.
    # ========================================================
    ordered_clusters = order_clusters(
        clusters,
        sink
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
    if total_nodes <= 0:
        raise ValueError(
            "Scenario must contain at least one node"
        )
    features["node_density"] = (
        total_nodes /
        area
    )
    # ========================================================
    # Network features
    # ========================================================
    features["relay_power"] = (
        float(relay_power)
    )
    features["node_power"] = (
        float(node_power)
    )
    features["relay_traffic"] = (
        float(relay_traffic)
    )
    features["node_traffic"] = (
        float(node_traffic)
    )
    features["propagation"] = (
        float(propagation)
    )
    features["packet_length"] = (
        float(packet_length)
    )
    features["interval"] = (
        float(interval)
    )
    features["simulated_range"] = (
        float(simulated_range)
    )
    features["node_to_relay_range"] = node_to_relay_range
    # ========================================================
    # Relay <-> Relay
    #
    # Do NOT use relay IDs as feature identities.
    #
    # Instead:
    #
    # relay_pair_distance_0 = shortest relay pair
    # relay_pair_distance_1 = second shortest
    # ...
    #
    # Normalized by calibrated relay-to-relay range.
    # ========================================================
    relay_pair_distances = []
    for i in range(
        len(relays)
    ):
        for j in range(
            i + 1,
            len(relays)
        ):
            d = distance(
                relays[i],
                relays[j]
            )
            relay_pair_distances.append(
                d /
                simulated_range
            )
    relay_pair_distances.sort()
    for i, value in enumerate(
        relay_pair_distances
    ):
        features[
            f"relay_pair_distance_{i}"
        ] = value
    # ========================================================
    # Relay <-> Sink
    #
    # Again: sorted scalar values rather than relay identities.
    #
    # relay_sink_distance_0 = closest relay to sink
    # relay_sink_distance_1 = second closest
    # ...
    #
    # Normalized by deployment-area diagonal.
    # ========================================================
    relay_sink_distances = []
    for relay in relays:
        d = distance(
            relay,
            sink
        )
        relay_sink_distances.append(
            d /
            area_diagonal
        )
    relay_sink_distances.sort()
    for i, value in enumerate(
        relay_sink_distances
    ):
        features[
            f"relay_sink_distance_{i}"
        ] = value
    # ========================================================
    # Cluster features
    # ========================================================
    total_nodes_covered_by_a_relay = 0

    for cluster_idx, cluster in enumerate(
        ordered_clusters
    ):
        centroid = cluster[
            "centroid"
        ]
        # ----------------------------------------------------
        # Population
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
        features[
            f"cluster_{cluster_idx}_sink_relative_distance"
        ] = (
            distance(
                centroid,
                sink
            ) /
            area_diagonal
        )
        # ----------------------------------------------------
        # Cluster <-> Relays
        #
        # Instead of:
        #
        # cluster_0 -> relay_0
        # cluster_0 -> relay_1
        #
        # use:
        #
        # cluster_0 -> nearest relay
        # cluster_0 -> second nearest relay
        # ...
        # ----------------------------------------------------
        cluster_relay_distances = []
        for relay in relays:
            d = distance(
                centroid,
                relay
            )
            cluster_relay_distances.append(
                d /
                area_diagonal
            )
        cluster_relay_distances.sort()
        for relay_rank, value in enumerate(
            cluster_relay_distances
        ):
            features[
                f"cluster_{cluster_idx}_relay_distance_{relay_rank}"
            ] = value

        # ----------------------------------------------------
        # Additional coverage features (v2.2)
        #
        # Work with the ORIGINAL sensor positions inside each
        # cluster, not merely its centroid and average radius.
        # A covered sensor is geometrically within calibrated
        # node-to-relay range; delivery is not guaranteed.
        # ----------------------------------------------------
        if "members" not in cluster:
            raise ValueError(
                "Clusters must retain their original sensor positions "
                "under the 'members' key. Use the updated build_clusters()."
            )

        members = np.asarray(cluster["members"], dtype=float)
        if (members.ndim != 2 or members.shape[1] != 2
                or len(members) != cluster["size"]
                or not np.isfinite(members).all()):
            raise ValueError("Invalid sensor positions in cluster members")

        # Matrix: one row per sensor, one column per relay.
        sensor_relay_distances = np.linalg.norm(
            members[:, None, :] - relay_positions[None, :, :],
            axis=2
        )
        nearest_distances = sensor_relay_distances.min(axis=1)
        any_relay_covered = nearest_distances <= node_to_relay_range
        count_any = int(any_relay_covered.sum())
        total_nodes_covered_by_a_relay += count_any

        # Select the relay closest to the CLUSTER CENTROID.
        # For an exact tie, take the best reachable count among
        # tied relays to avoid dependence on arbitrary relay IDs.
        centroid_relay_distances = np.linalg.norm(
            relay_positions - centroid,
            axis=1
        )
        nearest_centroid_distance = centroid_relay_distances.min()
        closest_relay_indices = np.flatnonzero(
            np.isclose(
                centroid_relay_distances,
                nearest_centroid_distance,
                rtol=1e-12,
                atol=1e-12
            )
        )
        count_centroid_closest = max(
            int((sensor_relay_distances[:, relay_idx]
                 <= node_to_relay_range).sum())
            for relay_idx in closest_relay_indices
        )

        features[
            f"cluster_{cluster_idx}_centroid_nearest_relay_covered_fraction"
        ] = count_centroid_closest / len(members)

        features[
            f"cluster_{cluster_idx}_any_relay_covered_fraction"
        ] = count_any / len(members)

        features[
            f"cluster_{cluster_idx}_mean_nearest_relay_distance_ratio"
        ] = float(nearest_distances.mean() / node_to_relay_range)

    # Summary across all sensor clusters.
    features["overall_any_relay_covered_fraction"] = (
        total_nodes_covered_by_a_relay / total_nodes
    )

    return features