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
#include "network_files.h"

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

constexpr std::string_view toString(Method method) {
    switch (method) {
        case Method::Simulation: return "Simulation";
        case Method::Surrogate:  return "Surrogate";
        case Method::Hybrid:     return "Hybrid";
    }

    return "Unknown";
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

            int result = std::system("./wsn_sim -u Cmdenv -f network/range_test.ini");

            if (result != 0)
                throw std::runtime_error("OMNeT++ simulation failed");

            double received = readScalar("network/range_test.sca", "packetsReceived");

            double sent = readScalar("network/range_test.sca", "packetsSent");

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

        if (average_pdr >= 0.95) {
            estimated_range = distance;
        }
        else {
            break;
        }
    }

    writeSimulationIni(scenario.network, "network/omnetpp.ini");

    // FALTA ENTAO ESCREVER O OMNETPP.INI

    // e daí é rodar..... e é isso aí....
    // cofigurar ned e ini direito
    // compilar e rodar

    // -> aqui / Só fazer config.ini do experimento na hora de rodar mesmo, escrever tudo dai..... o omnetpp.ini que vai ser FIXO

    scenario.network.simulated_range[{NodeType::Relay, NodeType::Relay}] = estimated_range;
    //scenario.network.simulated_range[{NodeType::Node, NodeType::Relay}] = estimated_range;
}

double runSimulation(const FixedSizeVector<Coordinates>& relays, const Scenario& scenario) {
    //writeOmnetConfig so posicoes 
    int result = std::system("./wsn_sim -u Cmdenv -f network/omnetpp.ini -f network/pso_positions.ini");

    if (result != 0)
        throw std::runtime_error("OMNeT++ simulation failed");

    //readFitness
}