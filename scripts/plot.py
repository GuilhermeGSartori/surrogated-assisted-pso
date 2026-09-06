import sys
import re
import matplotlib.pyplot as plt


LOG_FILE = "../../build/logs/final_log.log"


def parse_log(filename):

    nodes = []
    relays = []

    area_width = None
    area_height = None

    reading_nodes = False
    reading_relays = False

    # Supports:
    # 10, 20
    # 10.5, 20.7
    # -10.5, 3.2
    # 1.2e+03, 4.5e-02
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
            # Sensor nodes section
            # ====================================================

            if line == "Nodes Positions:":

                reading_nodes = True
                reading_relays = False

                continue


            if reading_nodes and line.startswith("All particles start"):

                reading_nodes = False

                continue


            # ====================================================
            # Final global best relays section
            # ====================================================

            if line == "Final global best relays:":

                reading_nodes = False
                reading_relays = True

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

                elif reading_relays:
                    relays.append(position)


    return area_width, area_height, nodes, relays


def plot_nodes(
    area_width,
    area_height,
    nodes,
    relays,
    output_file
):

    node_x = [node[0] for node in nodes]
    node_y = [node[1] for node in nodes]

    relay_x = [relay[0] for relay in relays]
    relay_y = [relay[1] for relay in relays]


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
    # Final global best relays
    # ============================================================

    plt.scatter(
        relay_x,
        relay_y,
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

    plt.title("Sensor Nodes and Final Global Best Relays")

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
            "Usage: python3 plot_nodes.py <output_file>"
        )

        sys.exit(1)


    output_file = sys.argv[1]


    area_width, area_height, nodes, relays = parse_log(
        LOG_FILE
    )


    if area_width is None or area_height is None:

        raise RuntimeError(
            "Could not find area dimensions in log."
        )


    if not nodes:

        raise RuntimeError(
            "No sensor nodes found in log."
        )


    if not relays:

        raise RuntimeError(
            "No final global best relay positions found in log."
        )


    print(f"Area: {area_width} x {area_height}")
    print(f"Sensor nodes found: {len(nodes)}")
    print(f"Final relays found: {len(relays)}")


    plot_nodes(
        area_width,
        area_height,
        nodes,
        relays,
        output_file
    )


if __name__ == "__main__":
    main()