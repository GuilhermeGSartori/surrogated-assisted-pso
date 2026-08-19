#include <fstream>
#include <sstream>
#include <string>
#include <random>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <iomanip>
#include <filesystem>
#include <string_view>

#include "aux.h"

Method parseMethod(const std::string& method) {

    if (method == "0")
        return Method::Simulation;

}

Scenario parseScenario(const std::string& filename)
{
    std::ifstream file(filename);

    if (!file.is_open()) {
        throw std::runtime_error("Could not open scenario file: " + filename);
    }

    std::string line;

    // Skip header
    if (!std::getline(file, line)) {
        throw std::runtime_error("Scenario file is empty");
    }

    // Read scenario data
    if (!std::getline(file, line)) {
        throw std::runtime_error("Scenario file has no scenario data");
    }

    std::stringstream ss(line);
    std::string value;

    Scenario scenario{};

    std::getline(ss, value, ',');
    scenario.n_relays = std::stoul(value);

    std::getline(ss, value, ',');
    scenario.seed = std::stoul(value);

    std::getline(ss, value, ',');
    scenario.n_nodes = std::stoul(value);

    std::getline(ss, value, ',');
    scenario.area.width = std::stod(value);

    std::getline(ss, value, ',');
    scenario.area.height = std::stod(value);

    std::getline(ss, value, ',');
    scenario.n_clusters = std::stoul(value);

    std::getline(ss, value, ',');
    scenario.sink.x = std::stod(value);

    std::getline(ss, value, ',');
    scenario.sink.y = std::stod(value);

    std::getline(ss, value, ',');
    scenario.network_config = std::stoul(value);

    return scenario;
}

template <typename Container>
void LHS(Container& nodes, std::size_t n, const Dimensions& area, std::mt19937& rng) {

    std::vector<std::size_t> x_strata(n);
    std::vector<std::size_t> y_strata(n);

    std::iota(x_strata.begin(), x_strata.end(), 0);
    std::iota(y_strata.begin(), y_strata.end(), 0);

    std::shuffle(x_strata.begin(), x_strata.end(), rng);
    std::shuffle(y_strata.begin(), y_strata.end(), rng);

    std::uniform_real_distribution<double> random(0.0, 1.0);

    for (std::size_t i = 0; i < n; ++i) {

        double x_normalized =
            (x_strata[i] + random(rng)) / static_cast<double>(n);

        double y_normalized =
            (y_strata[i] + random(rng)) / static_cast<double>(n);

        nodes[i].x = x_normalized * area.width;
        nodes[i].y = y_normalized * area.height;
    }
}

template <typename T>
void FixedSizeVector<T>::checkSameSize(const FixedSizeVector& other) const {
    if (size() != other.size()) {
        throw std::length_error("FixedSizeVector size mismatch");
    }
}

double Coordinates::distanceSquared(const Coordinates& a, const Coordinates& b) {
    Coordinates d = a - b;
    return d.x*d.x + d.y*d.y;
}

std::ofstream createLogFile() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t time = std::chrono::system_clock::to_time_t(now);

    std::tm tm{};
    localtime_r(&time, &tm);   // Linux

    std::ostringstream filename;

    filename << std::put_time(&tm, "%Y-%m-%d_%H-%M-%S")
             << ".log";

    std::ofstream log(filename.str());

    if (!log.is_open()) {
        throw std::runtime_error("Could not create log file");
    }

    return log;
}

void configNetwork(Scenario& scenario) {

    scenario.network = parseNetworkConfig(scenario.network_config, "scenarions");

    // config .ini file --> aqui já escrever tudo, só vai faltar as posicoes
    // run simulation to figure it out distance

    scenario.network.simulated_range[{NodeType::Relay, NodeType::Relay}] = 0.0;
    scenario.network.simulated_range[{NodeType::Node, NodeType::Relay}] = 0.0;
}

constexpr std::string_view toString(Method method) {
    switch (method) {
        case Method::Simulation: return "Simulation";
        case Method::Surrogate:  return "Surrogate";
        case Method::Hybrid:     return "Hybrid";
    }

    return "Unknown";
}

double runSimulation(const FixedSizeVector<Coordinates>& relays, const Scenario& scenario) {
    //writeOmnetConfig so posicoes
    int result = std::system("./wsn_sim -u Cmdenv -f omnetpp.ini -f pso_positions.ini");

    if (result != 0)
        throw std::runtime_error("OMNeT++ simulation failed");

    //readFitness
}

std::vector<std::string> splitCSV(const std::string& line) {
    std::vector<std::string> values;
    std::stringstream ss(line);
    std::string value;

    while (std::getline(ss, value, ',')) {
        values.push_back(value);
    }

    return values;
}

Network parseNetworkConfig(unsigned int config_number, const std::filesystem::path& network_directory) {
    const std::filesystem::path file_path =
        network_directory /
        ("network_" + std::to_string(config_number) + ".csv");

    std::ifstream file(file_path);

    if (!file) {
        throw std::runtime_error(
            "Could not open network configuration file: " +
            file_path.string()
        );
    }

    std::string header;
    std::string row;

    // Read header
    if (!std::getline(file, header)) {
        throw std::runtime_error(
            "Network configuration file has no header: " +
            file_path.string()
        );
    }

    // Read configuration row
    if (!std::getline(file, row)) {
        throw std::runtime_error(
            "Network configuration file has no data: " +
            file_path.string()
        );
    }

    const std::vector<std::string> values = splitCSV(row);

    if (values.size() != 17) {
        throw std::runtime_error(
            "Invalid network configuration. Expected 17 fields, got " +
            std::to_string(values.size()) +
            " in file: " +
            file_path.string()
        );
    }

    Network network;

    // ============================================================
    // Relay configuration
    // ============================================================

    network.interface[NodeType::Relay] =
        std::stoul(values[0]);

    network.frequency[NodeType::Relay] =
        std::stod(values[1]);

    network.bandwidth[NodeType::Relay] =
        std::stod(values[2]);

    network.bitrate[NodeType::Relay] =
        std::stod(values[3]);

    network.power[NodeType::Relay] =
        std::stod(values[4]);

    network.propagation[NodeType::Relay] =
        std::stoul(values[5]);

    network.traffic[NodeType::Relay] =
        std::stoul(values[6]);


    // ============================================================
    // Sensor/node configuration
    // ============================================================

    network.interface[NodeType::Node] =
        std::stoul(values[7]);

    network.frequency[NodeType::Node] =
        std::stod(values[8]);

    network.bandwidth[NodeType::Node] =
        std::stod(values[9]);

    network.bitrate[NodeType::Node] =
        std::stod(values[10]);

    network.power[NodeType::Node] =
        std::stod(values[11]);

    network.propagation[NodeType::Node] =
        std::stoul(values[12]);

    network.traffic[NodeType::Node] =
        std::stoul(values[13]);


    // ============================================================
    // Shared network parameters
    // ============================================================

    network.packet_length =
        std::stoul(values[14]);

    network.interval =
        std::stod(values[15]);

    network.seed =
        std::stoul(values[16]);

    return network;
}