import sys
import re
import matplotlib.pyplot as plt


LOG_FILE = "../../build/logs/final_log.log"


def parse_log(filename):

    nodes = []
    first_relays = []
    final_relays = []

    area_width = None
    area_height = None

    reading_nodes = False
    reading_first_relays = False
    reading_final_relays = False

    coordinate_pattern = re.compile(
        r"^\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        r"\s*,\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        r"\s*$"
    )

    with open(filename, "r") as file:

        for line in file:

            line = line.strip()

            # ====================================================
            # Area
            # ====================================================

            if line.startswith("Area:"):

                match = re.search(
                    r"Area:\s*([\d.]+)\s*x\s*([\d.]+)",
                    line
                )

                if match:
                    area_width = float(match.group(1))
                    area_height = float(match.group(2))

                continue


            # ====================================================
            # Sensor nodes
            # ====================================================

            if line == "Nodes Positions:":

                reading_nodes = True
                reading_first_relays = False
                reading_final_relays = False

                continue


            # ====================================================
            # Initial relay positions
            # ====================================================

            if line == "First Relays:":

                reading_nodes = False
                reading_first_relays = True
                reading_final_relays = False

                continue


            # ====================================================
            # Final global best relay positions
            # ====================================================

            if line == "Final global best relays:":

                reading_nodes = False
                reading_first_relays = False
                reading_final_relays = True

                continue


            # ====================================================
            # Coordinate parsing
            # ====================================================

            match = coordinate_pattern.match(line)

            if match:

                position = (
                    float(match.group(1)),
                    float(match.group(2))
                )

                if reading_nodes:
                    nodes.append(position)

                elif reading_first_relays:
                    first_relays.append(position)

                elif reading_final_relays:
                    final_relays.append(position)


    return (
        area_width,
        area_height,
        nodes,
        first_relays,
        final_relays
    )


def plot_nodes(
    area_width,
    area_height,
    nodes,
    first_relays,
    final_relays,
    output_file
):

    node_x = [node[0] for node in nodes]
    node_y = [node[1] for node in nodes]

    first_relay_x = [relay[0] for relay in first_relays]
    first_relay_y = [relay[1] for relay in first_relays]

    final_relay_x = [relay[0] for relay in final_relays]
    final_relay_y = [relay[1] for relay in final_relays]


    plt.figure(figsize=(8, 8))


    # ============================================================
    # Sensor nodes
    # ============================================================

    plt.scatter(
        node_x,
        node_y,
        color="blue",
        marker="o",
        label="Sensor Nodes"
    )


    # ============================================================
    # Initial relay positions
    # ============================================================

    plt.scatter(
        first_relay_x,
        first_relay_y,
        color="green",
        marker="x",
        s=100,
        linewidths=2,
        label="Initial Relays"
    )


    # ============================================================
    # Final global best relay positions
    # ============================================================

    plt.scatter(
        final_relay_x,
        final_relay_y,
        color="red",
        marker="x",
        s=100,
        linewidths=2,
        label="Final Global Best Relays"
    )


    # ============================================================
    # Plot configuration
    # ============================================================

    plt.xlim(0, area_width)
    plt.ylim(0, area_height)

    plt.xlabel("X")
    plt.ylabel("Y")

    plt.title(
        "Sensor Nodes, Initial Relays and Final Global Best Relays"
    )

    plt.grid(True)
    plt.legend()

    plt.gca().set_aspect(
        "equal",
        adjustable="box"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def main():

    if len(sys.argv) != 2:

        print(
            "Usage: python3 plot.py <output_file>"
        )

        sys.exit(1)


    output_file = sys.argv[1]


    (
        area_width,
        area_height,
        nodes,
        first_relays,
        final_relays
    ) = parse_log(LOG_FILE)


    if area_width is None or area_height is None:

        raise RuntimeError(
            "Could not find area dimensions in log."
        )


    if not nodes:

        raise RuntimeError(
            "No sensor nodes found in log."
        )


    if not first_relays:

        raise RuntimeError(
            "No initial relay positions found in log."
        )


    if not final_relays:

        raise RuntimeError(
            "No final global best relay positions found in log."
        )


    print(f"Area: {area_width} x {area_height}")
    print(f"Sensor nodes found: {len(nodes)}")
    print(f"Initial relays found: {len(first_relays)}")
    print(f"Final relays found: {len(final_relays)}")


    plot_nodes(
        area_width,
        area_height,
        nodes,
        first_relays,
        final_relays,
        output_file
    )


if __name__ == "__main__":
    main()