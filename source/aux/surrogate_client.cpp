#include "aux.h"

#include <iostream>
#include <string>
#include <cstring>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

void appendNodes(const std::vector<Coordinates>& nodes, std::string& packet, int n_clusters) {
    
    packet += "*,";
    for (const auto& c : nodes) {
        packet += std::to_string(c.x) + ",";
        packet += std::to_string(c.y) + ",";
    }
    packet += std::to_string(n_clusters);
    packet += '\n';
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
    std::to_string(network.interval) + "," +
    std::to_string(network.simulated_range.at({NodeType::Relay, NodeType::Relay}));
    
    return packet;
}

double sendPacket(const std::string& packet) {
    int clientSocket = socket(AF_INET, SOCK_STREAM, 0);

    if (clientSocket < 0) {
        perror("socket");
        return -1.0;
    }

    sockaddr_in serverAddress{};
    serverAddress.sin_family = AF_INET;
    serverAddress.sin_port = htons(8080);

    inet_pton(AF_INET, "127.0.0.1", &serverAddress.sin_addr);


    if (connect(clientSocket, reinterpret_cast<sockaddr*>(&serverAddress), sizeof(serverAddress)) < 0) {
        perror("connect");
        close(clientSocket);
        return -1.0;
    }

    ssize_t sent = send(clientSocket, packet.data(), packet.size(), 0);

    if (sent < 0) {
        perror("send");
        close(clientSocket);
        return -1.0;
    }

    // Wait for response
    char buffer[1024];
    ssize_t received = recv(clientSocket, buffer,  sizeof(buffer) - 1, 0);
 
    if (received <= 0) {
        perror("recv");
        close(clientSocket);
        return -1.0;
    }

    buffer[received] = '\0';

    close(clientSocket);

    return std::stod(buffer);
}
