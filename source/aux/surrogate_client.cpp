#include "aux.h"

#include <string>

void appendNodes(const std::vector<Coordinates>& nodes, std::string& packet, int n_clusters) {

    packet += "*,";
    for (const auto& c : nodes) {
        packet += std::to_string(c.x) + "," + packet += std::to_string(c.y) + ",";
    }
    packet += std::to_string(n_clusters);
}

std::string generatePacket(const FixedSizeVector<Coordinates>& relays, const Scenario& scenario) {
    const Network& network = scenario.network;

    std::string packet =
    std::to_string(scenario.area.width) + "," +
    std::to_string(scenario.area.height) + "," +
    std::to_string(scenario.sink.x) + "," +
    std::to_string(scenario.sink.y) + ",";

    for (std::size_t i = 0; i < scenario.n_relays; ++i) {
        packet += std::to_string(relays[i].x) + "," + std::to_string(relays[i].y) + ",";
    }

    packet += 
    std::to_string(network.interface.at(NodeType::Relay)) + "," +
    std::to_string(network.frequency.at(NodeType::Relay)) + "," +
    std::to_string(network.bandwidth.at(NodeType::Relay)) + "," +
    std::to_string(network.bitrate.at(NodeType::Relay)) + "," +
    std::to_string(network.power.at(NodeType::Relay)) + "," +
    std::to_string(network.traffic.at(NodeType::Relay)) + "," +
    
    std::to_string(network.interface.at(NodeType::Node)) + "," +
    std::to_string(network.frequency.at(NodeType::Node)) + "," +
    std::to_string(network.bandwidth.at(NodeType::Node)) + "," +
    std::to_string(network.bitrate.at(NodeType::Node)) + "," +
    std::to_string(network.power.at(NodeType::Node)) + "," +
    std::to_string(network.traffic.at(NodeType::Node)) + "," +

    std::to_string(network.propagation) + "," +
    std::to_string(network.packet_length) + "," +
    std::to_string(network.interval);
    
    return packet;
}

double sendPacket(std::string packet) {
    return 0.0;
}