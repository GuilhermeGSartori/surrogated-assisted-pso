#include <random>
#include <algorithm>
#include <fstream>

#include "trainer.h"

void writeDatasetHeader(std::ofstream& file, std::size_t n_relays) {
    file
        << "scenario_id,"
        << "sample_id,"
        << "area_width,"
        << "area_height,"
        << "sink_x,"
        << "sink_y,"
        << "n_relays,";

    for (std::size_t i = 0; i < n_relays; ++i) {
        file
            << "relay_" << i << "_x,"
            << "relay_" << i << "_y,";
    }

    file
        << "relay_interface,"
        << "relay_frequency,"
        << "relay_bandwidth,"
        << "relay_bitrate,"
        << "relay_power,"
        << "relay_traffic,"
        << "node_interface,"
        << "node_frequency,"
        << "node_bandwidth,"
        << "node_bitrate,"
        << "node_power,"
        << "node_traffic,"
        << "propagation,"
        << "packet_length,"
        << "interval,"
        << "network_seed,"
        << "fitness\n";
}

void writeNodesHeader(std::ofstream& file) {
    file
        << "scenario_id,"
        << "n_clusters,"
        << "n_nodes,"
        << "node_id,"
        << "x,"
        << "y\n";
}

void writeNodesScenario(std::ofstream& file, std::size_t scenario_id, const Scenario& scenario) {
    for (std::size_t i = 0; i < scenario.nodes.size(); ++i) {

        file
            << scenario_id << ','
            << scenario.n_clusters << ','
            << scenario.n_nodes << ','
            << i << ','
            << scenario.nodes[i].x << ','
            << scenario.nodes[i].y
            << '\n';
    }
}

void writeDatasetRow(std::ofstream& file, std::size_t scenario_id, std::size_t sample_id, const Scenario& scenario, const FixedSizeVector<Coordinates>& relays, double fitness) {
    const Network& network = scenario.network;

    file
        << scenario_id << ','
        << sample_id << ','
        << scenario.area.width << ','
        << scenario.area.height << ','
        << scenario.sink.x << ','
        << scenario.sink.y << ','
        << scenario.n_relays << ',';

    for (const auto& relay : relays) {
        file
            << relay.x << ','
            << relay.y << ',';
    }

    file
        << network.interface.at(NodeType::Relay) << ','
        << network.frequency.at(NodeType::Relay) << ','
        << network.bandwidth.at(NodeType::Relay) << ','
        << network.bitrate.at(NodeType::Relay) << ','
        << network.power.at(NodeType::Relay) << ','
        << network.traffic.at(NodeType::Relay) << ','

        << network.interface.at(NodeType::Node) << ','
        << network.frequency.at(NodeType::Node) << ','
        << network.bandwidth.at(NodeType::Node) << ','
        << network.bitrate.at(NodeType::Node) << ','
        << network.power.at(NodeType::Node) << ','
        << network.traffic.at(NodeType::Node) << ','

        << network.propagation << ','
        << network.packet_length << ','
        << network.interval << ','
        << network.seed << ','

        << fitness
        << '\n';
}

void generateDataset(Scenario& scenario) {

    FixedSizeVector<Coordinates> relays(scenario.n_relays);

    configNetwork(scenario);

    double range = scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay});

    std::ofstream dataset("../surrogate_model/data/dataset.csv");
    std::ofstream nodes_file("../surrogate_model/data/nodes.csv");

    if (!dataset || !nodes_file) {
        throw std::runtime_error(
            "Could not create dataset files"
        );
    }

    writeDatasetHeader(dataset, scenario.n_relays);
    writeNodesHeader(nodes_file);

    for (int i = 0; i < 100; ++i) {
        std::mt19937 rng(scenario.seed*i);
        LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);
        writeNodePositions(scenario.nodes, scenario.sink, "network/sensor_nodes.ini");
        do {
            LHS(relays, scenario.n_relays, scenario.area, rng);
        } while (!isConnected(relays, scenario.sink, range));

        writeNodesScenario(nodes_file, i, scenario);

        FixedSizeVector<Coordinates> initial_relays = relays;

        std::uniform_real_distribution<double> noise(-5.0, 5.0);
        
        for (int j = 0; j < 20; ++j) {
            double fitness = runSimulation(relays, scenario);

            writeDatasetRow(dataset, i, j, scenario, relays, fitness);
            
            relays = initial_relays;

            for (auto& relay : relays) {
                relay += Coordinates{noise(rng), noise(rng)};
            
                relay.x = std::clamp(relay.x, 0.0, scenario.area.width);
                relay.y = std::clamp(relay.y, 0.0, scenario.area.height);
            }
        }

    }
}