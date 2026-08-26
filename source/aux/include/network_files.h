#pragma once

#include <map>
#include <unordered_map>
#include <utility>
#include <cstddef>
#include <string>
#include <vector>
#include <stdexcept>
#include <string_view>
#include <filesystem>

enum class NodeType {
    Node,
    Relay
};

struct Network {
    std::unordered_map<NodeType, unsigned int> interface;

    std::unordered_map<NodeType, double> frequency;
    std::unordered_map<NodeType, double> bandwidth;
    std::unordered_map<NodeType, double> bitrate;
    std::unordered_map<NodeType, double> power;

    unsigned int propagation;
    std::unordered_map<NodeType, unsigned int> traffic;

    unsigned int packet_length = 0;
    double interval = 0.0;

    unsigned int seed = 0;

    std::map<std::pair<NodeType, NodeType>, double> simulated_range;

    // fixed in .ini: energy model (batery), traffic source, forwards, dest
};

double readScalar(const std::string& filename, const std::string& scalarName);

std::vector<std::string> splitCSV(const std::string& line);

Network parseNetworkConfig(unsigned int config_number, const std::filesystem::path& network_directory);

void writeDistanceExperimentIni(const Network& network, NodeType transmitter_type, NodeType receiver_type, double distance, const std::filesystem::path& output_file);

void writeSimulationIni(std::size_t num_nodes, std::size_t num_relays, Network network, const std::filesystem::path& output_file);

std::string getTrafficName(unsigned int id);

std::string getPropagationName(unsigned int id);

std::string getInterfaceName(unsigned int id);