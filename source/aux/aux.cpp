#include <iostream>
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

    return Method::Simulation;

}

Scenario parseScenario(const std::string& filename) {
    const std::filesystem::path file_path =
        "scenarios/" + filename + ".csv";
        
    std::ifstream file(file_path);

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

    scenario.nodes.resize(scenario.n_nodes);

    return scenario;
}

double Coordinates::distanceSquared(const Coordinates& a, const Coordinates& b) {
    Coordinates d = a - b;
    return d.x*d.x + d.y*d.y;
}

std::ofstream createLogFile() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t time = std::chrono::system_clock::to_time_t(now);

    std::tm tm{};
    localtime_r(&time, &tm);

    std::ostringstream filename;

    filename << std::put_time(&tm, "%Y-%m-%d_%H-%M-%S")
             << ".log";

    std::filesystem::path log_dir = "logs";

    // Creates logs/ if it doesn't exist
    std::filesystem::create_directories(log_dir);

    std::filesystem::path log_path = log_dir / filename.str();

    std::ofstream log(log_path);

    if (!log.is_open()) {
        throw std::runtime_error("Could not create log file");
    }

    return log;
}

void configNetwork(Scenario& scenario) {

    scenario.network = parseNetworkConfig(scenario.network_config, "scenarios");
    double estimated_range = 0.0;

    for (double distance = 5.0; distance <= 300.0; distance += 5.0) {
        constexpr int repetitions = 10;

        double total_pdr = 0.0;

        for (int i = 0; i < repetitions; ++i) {

            writeDistanceExperimentIni(scenario.network, NodeType::Relay, NodeType::Relay, distance, "network/range_test.ini");

            std::filesystem::remove("network/range_test.sca");

            int result = std::system(
                                        "opp_run "
                                        "-u Cmdenv "
                                        "-n network:$INET_ROOT/src "
                                        "-l $INET_ROOT/src/INET "
                                        "-f network/range_test.ini"
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

            total_pdr += pdr;
        }

        const double average_pdr =
            total_pdr / repetitions;

        std::cout << "Average pdr: " << average_pdr << "\n";

        if (average_pdr >= 0.95) {
            estimated_range = distance;
        }
        else {
            break;
        }
    }

    writeSimulationIni(scenario.n_nodes, scenario.n_relays, scenario.network, "network/omnetpp.ini");

    scenario.network.simulated_range[{NodeType::Relay, NodeType::Relay}] = estimated_range;
    scenario.network.simulated_range[{NodeType::Node, NodeType::Relay}] = estimated_range/2;
}

void writeNodePositions(const std::vector<Coordinates>& nodes, Coordinates sink, const std::filesystem::path& output_file) {

    std::ofstream ini(output_file);

    if (!ini) {
        throw std::runtime_error(
            "Could not create OMNeT++ position file: " +
            output_file.string()
        );
    }

    ini << "[General]\n\n";

    for (std::size_t i = 0; i < nodes.size(); ++i) {
        ini << "*.node[" << i << "].mobility.initialX = " << nodes[i].x << "m\n";
        ini << "*.node[" << i << "].mobility.initialY = " << nodes[i].y << "m\n";
    }

    ini << "**.sink.mobility.initialX = " << sink.x << "m\n";
    ini << "**.sink.mobility.initialY = " << sink.y << "m\n";
}

void writeRelayPositions(const FixedSizeVector<Coordinates>& relays, const std::filesystem::path& output_file) {

    std::ofstream ini(output_file);

    if (!ini) {
        throw std::runtime_error(
            "Could not create OMNeT++ position file: " +
            output_file.string()
        );
    }

    ini << "[General]\n\n";

    for (std::size_t i = 0; i < relays.size(); ++i) {
        ini << "*.relay[" << i << "].mobility.initialX = " << relays[i].x << "m\n";
        ini << "*.relay[" << i << "].mobility.initialY = " << relays[i].y << "m\n";
    }
}

double runSimulation(const FixedSizeVector<Coordinates>& relays, const Scenario& scenario) {
    writeRelayPositions(relays, "network/pso_positions.ini");

    int result = std::system("./wsn_sim -u Cmdenv -f network/omnetpp.ini -f network/sensor_nodes.ini -f network/pso_positions.ini");

    if (result != 0)
        throw std::runtime_error("OMNeT++ simulation failed");

    double received = readScalar("network/range_test.sca", "aa", "packetsReceived");
    double sent = readScalar("network/range_test.sca", "aa", "packetsSent");

    if (sent == 0) {
        throw std::runtime_error("Simulation sent zero packets");
    }

    return static_cast<double>(received) / sent;
}