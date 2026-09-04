import sys
import re
import matplotlib.pyplot as plt


LOG_FILE = "pso_log.txt"


def parse_log(filename):
    nodes = []
    area_width = None
    area_height = None

    reading_nodes = False

    with open(filename, "r") as file:
        for line in file:
            line = line.strip()

            if line.startswith("Area:"):
                match = re.search(
                    r"Area:\s*([\d.]+)\s*x\s*([\d.]+)",
                    line
                )

                if match:
                    area_width = float(match.group(1))
                    area_height = float(match.group(2))

            elif line == "Nodes Positions:":
                reading_nodes = True
                continue

            elif reading_nodes and line.startswith(
                "All particles start"
            ):
                reading_nodes = False
                continue

            elif reading_nodes:
                match = re.match(
                    r"^\s*([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)\s*$",
                    line
                )

                if match:
                    nodes.append(
                        (
                            float(match.group(1)),
                            float(match.group(2))
                        )
                    )

    return area_width, area_height, nodes


def plot_nodes(area_width, area_height, nodes, output_file):
    x = [node[0] for node in nodes]
    y = [node[1] for node in nodes]

    plt.figure(figsize=(8, 8))

    plt.scatter(x, y)

    plt.xlim(0, area_width)
    plt.ylim(0, area_height)

    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("Sensor Node Positions")

    plt.grid(True)
    plt.gca().set_aspect("equal", adjustable="box")

    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 plot_nodes.py <output_file>")
        sys.exit(1)

    output_file = sys.argv[1]

    area_width, area_height, nodes = parse_log(LOG_FILE)

    if area_width is None or area_height is None:
        raise RuntimeError("Could not find area dimensions in log.")

    if not nodes:
        raise RuntimeError("No nodes found in log.")

    plot_nodes(
        area_width,
        area_height,
        nodes,
        output_file
    )


if __name__ == "__main__":
    main()