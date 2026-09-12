#include <random>
#include <algorithm>
#include <fstream>
#include <iostream>

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
        << "simulated_range,"
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

        << network.simulated_range.at({NodeType::Relay, NodeType::Relay}) << ','

        << fitness
        << '\n';
}

void generateDataset(TrainingScenario& scenario) {

    FixedSizeVector<Coordinates> relays(scenario.n_relays);

    std::ofstream dataset("../surrogate_model/data/dataset.csv");
    std::ofstream nodes_file("../surrogate_model/data/nodes.csv");

    if (!dataset || !nodes_file) {
        throw std::runtime_error(
            "Could not create dataset files"
        );
    }

    writeDatasetHeader(dataset, scenario.n_relays);
    writeNodesHeader(nodes_file);

    scenario.network = parseNetworkConfig(scenario.network_config, "scenarios");

    std::vector<double> simulated_ranges(num_of_powers);

    for (int i = 0; i < num_of_powers; ++i) {
        scenario.network.power[NodeType::Relay] = getPower(i);
        for (double distance = 5.0; distance <= 300.0; distance += 5.0) {
            writeDistanceExperimentIni(scenario.network, NodeType::Relay, NodeType::Relay, distance, "network/range_test.ini");
            std::filesystem::remove("network/range_test.sca");
            int result = std::system(
                                        "opp_run "
                                        "-u Cmdenv "
                                        "-n network:$INET_ROOT/src "
                                        "-l $INET_ROOT/src/INET "
                                        "-f network/range_test.ini "
                                        "> /dev/null"
                                    );
            if (result != 0)
                throw std::runtime_error("OMNeT++ simulation failed");
            double received = readScalar("network/range_test.sca", "RangeCalibration.rx.app[0]", "packetReceived:count");
            double sent = readScalar("network/range_test.sca", "RangeCalibration.tx.app[0]", "packetSent:count");
            if (sent == 0) {
                throw std::runtime_error(
                    "Distance experiment sent zero packets"
                );
            }
            const double pdr = static_cast<double>(received) / sent;
            if (pdr >= 0.95) {
                simulated_ranges[i] = distance;
            }   
            else {
                break;
            }
        }
        
    }

    for (int i = 0; i < 1000; ++i) {
        std::cout << ">> Seed: " << i << "\n";
        std::mt19937 rng(scenario.seed*i);
        
        std::uniform_real_distribution<double> area_width_dist(scenario.area_min.width, scenario.area_max.width);
        std::uniform_real_distribution<double> area_height_dist(scenario.area_min.height, scenario.area_max.height);
        std::uniform_int_distribution<int> node_dist(scenario.n_nodes_min,scenario.n_nodes_max);
        std::uniform_int_distribution<int> power_relay_dist(0, 2);
        std::uniform_int_distribution<int> power_node_dist(0, 2);
        //std::uniform_int_distribution<unsigned int> propagation_dist(0, 1);

        scenario.area.height = area_height_dist(rng);
        scenario.area.width = area_width_dist(rng);
        scenario.n_nodes = node_dist(rng);

        //scenario.network.propagation = propagation_dist(rng);

        int selected_relay_power = power_relay_dist(rng);
        int selected_node_power = power_node_dist(rng);
        scenario.network.power[NodeType::Relay] = getPower(selected_relay_power);
        scenario.network.power[NodeType::Node] = getPower(selected_node_power);

        scenario.network.simulated_range[{NodeType::Relay, NodeType::Relay}] = simulated_ranges[selected_relay_power];

        std::uniform_real_distribution<double> sink_x_dist(0.0, scenario.area.width);
        std::uniform_real_distribution<double> sink_y_dist(0.0, scenario.area.height);

        scenario.sink.x = sink_x_dist(rng);
        scenario.sink.y = sink_y_dist(rng);
   
        writeSimulationIni(scenario.n_nodes, scenario.n_relays, scenario.network, "network/omnetpp.ini");
        double range = scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay});

        scenario.nodes.resize(scenario.n_nodes);
        LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);
        writeNodePositions(scenario.nodes, scenario.sink, "network/sensor_nodes.ini");
        do {
            LHS(relays, scenario.n_relays, scenario.area, rng);
        } while (!isConnected(relays, scenario.sink, range));

        std::cout << "Found initial relay positions!\n";

        writeNodesScenario(nodes_file, i, scenario);

        FixedSizeVector<Coordinates> initial_relays = relays;

        std::uniform_real_distribution<double> noise(-80.0, 80.0);
        
        for (int j = 0; j < 10; ++j) {
            std::cout << ":>>>> Simulation: " << j << "\n"; 
            
            if (j == 0) {
            	relays = initial_relays;
            }
            else {
            	bool connected = false;
            	
            	constexpr int MAX_ATTEMPTS = 1000;
            	
            	for (int attempt = 0; attempt < MAX_ATTEMPTS; ++attempt) {
            	    relays = initial_relays;
            	    
            	    for (auto& relay : relays) {
                	relay += Coordinates{noise(rng), noise(rng)};
            
                	relay.x = std::clamp(relay.x, 0.0, scenario.area.width);
                	relay.y = std::clamp(relay.y, 0.0, scenario.area.height);
            	    }
            	    
            	    connected = isConnected(relays, scenario.sink, range);
            	    
            	    if (connected)
            	    	break;
            	}
            	
            	if (!connected) {
            	    throw std::runtime_error ("Could not generate a connected relay sample");
            	}
            }

            double fitness = runSimulation(relays, scenario);

            writeDatasetRow(dataset, i, j, scenario, relays, fitness);
        }

    }
}
