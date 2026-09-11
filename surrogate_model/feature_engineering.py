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
    clusters
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


    return features