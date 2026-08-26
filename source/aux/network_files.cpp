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

#include "network_files.h"

std::string getInterfaceName(unsigned int id) {
    switch (id) {
        case 0:
            return "Ieee802154NarrowbandInterface";

        default:
            throw std::runtime_error(
                "Unknown network interface ID: " +
                std::to_string(id)
            );
    }
}


std::string getPropagationName(unsigned int id) {
    switch (id) {
        case 0:
            return "BreakpointPathLoss";

        case 1:
            return "FreeSpacePathLoss";

        default:
            throw std::runtime_error(
                "Unknown propagation model ID: " +
                std::to_string(id)
            );
    }
}


std::string getTrafficName(unsigned int id) {
    switch (id) {
        case 0:
            return "UdpBasicApp";

        default:
            throw std::runtime_error(
                "Unknown traffic model ID: " +
                std::to_string(id)
            );
    }
}


void writeDistanceExperimentIni(const Network& network, NodeType transmitter_type, NodeType receiver_type, double distance, const std::filesystem::path& output_file) {
    if (distance <= 0.0) {
        throw std::runtime_error(
            "Distance must be greater than zero"
        );
    }

    const unsigned int propagation = network.propagation;

    static u_int8_t seed_counter = 1;

    std::ofstream ini(output_file);

    if (!ini) {
        throw std::runtime_error(
            "Could not create OMNeT++ ini file: " +
            output_file.string()
        );
    }


    // ============================================================
    // General simulation configuration
    // ============================================================

    ini << "[General]\n\n";

    ini << "network = RangeCalibration\n";

    // Enough time to send several packets.
    ini << "sim-time-limit = 30s\n";

    ini << "seed-set = "
        << network.seed + (seed_counter*100)
        << "\n\n";


    // ============================================================
    // Wireless medium
    // ============================================================

    ini << "# Wireless propagation model\n";

    ini << "*.radioMedium.pathLoss.typename = \""
        << getPropagationName(propagation)
        << "\"\n\n";


    // ============================================================
    // Transmitter interface
    // ============================================================

    ini << "# Transmitter radio\n";

    ini << "*.tx.wlan[0].typename = \""
        << getInterfaceName(
               network.interface.at(transmitter_type)
           )
        << "\"\n";

    ini << "*.tx.wlan[0].radio.centerFrequency = "
        << network.frequency.at(transmitter_type)
        << "Hz\n";

    ini << "*.tx.wlan[0].radio.bandwidth = "
        << network.bandwidth.at(transmitter_type)
        << "Hz\n";

    ini << "*.tx.wlan[0].radio.*.bitrate = "
        << network.bitrate.at(transmitter_type)
        << "bps\n";

    ini << "*.tx.wlan[0].radio.transmitter.power = "
        << network.power.at(transmitter_type)
        << "W\n\n";


    // ============================================================
    // Receiver interface
    // ============================================================

    ini << "# Receiver radio\n";

    ini << "*.rx.wlan[0].typename = \""
        << getInterfaceName(
               network.interface.at(receiver_type)
           )
        << "\"\n";

    ini << "*.rx.wlan[0].radio.centerFrequency = "
        << network.frequency.at(receiver_type)
        << "Hz\n";

    ini << "*.rx.wlan[0].radio.bandwidth = "
        << network.bandwidth.at(receiver_type)
        << "Hz\n";

    ini << "*.rx.wlan[0].radio.*.bitrate = "
        << network.bitrate.at(receiver_type)
        << "bps\n";

    /*
     * The receiver can transmit IEEE 802.15.4 ACKs, so its
     * transmission power is configured as well.
     */
    ini << "*.rx.wlan[0].radio.transmitter.power = "
        << network.power.at(receiver_type)
        << "W\n\n";


    // ============================================================
    // Positions
    //
    // tx = (0, 0)
    // rx = (distance, 0)
    // ============================================================

    ini << "# Positions\n";

    ini << "*.tx.mobility.typename = \"StationaryMobility\"\n";
    ini << "*.tx.mobility.initialX = 0m\n";
    ini << "*.tx.mobility.initialY = 0m\n";
    ini << "*.tx.mobility.initialZ = 0m\n\n";

    ini << "*.rx.mobility.typename = \"StationaryMobility\"\n";
    ini << "*.rx.mobility.initialX = "
        << distance
        << "m\n";

    ini << "*.rx.mobility.initialY = 0m\n";
    ini << "*.rx.mobility.initialZ = 0m\n\n";


    // ============================================================
    // Traffic generator
    // ============================================================

    ini << "# Traffic\n";

    ini << "*.tx.numApps = 1\n";

    ini << "*.tx.app[0].typename = \""
        << getTrafficName(
               network.traffic.at(transmitter_type)
           )
        << "\"\n";

    ini << "*.tx.app[0].destAddresses = \"rx\"\n";
    ini << "*.tx.app[0].destPort = 5000\n";

    ini << "*.tx.app[0].messageLength = "
        << network.packet_length
        << "B\n";

    ini << "*.tx.app[0].sendInterval = "
        << network.interval
        << "s\n";

    ini << "*.tx.app[0].startTime = 1s\n\n";


    // ============================================================
    // Receiver application
    // ============================================================

    ini << "*.rx.numApps = 1\n";
    ini << "*.rx.app[0].typename = \"UdpSink\"\n";
    ini << "*.rx.app[0].localPort = 5000\n\n";


    // ============================================================
    // Address resolution
    // ============================================================

    ini << "**.arp.typename = \"GlobalArp\"\n\n";


    // ============================================================
    // Results
    // ============================================================

    ini << "# Store scalars, avoid large vector result files\n";
    ini << "**.scalar-recording = true\n";
    ini << "**.vector-recording = false\n";

    ini << "output-scalar-file = network/range_test.sca\n";

    seed_counter++;
}

void writeSimulationIni(std::size_t num_nodes, std::size_t num_relays, Network network, const std::filesystem::path& output_file) {

    const unsigned int propagation = network.propagation;

    static u_int16_t seed_counter = 1;

    std::ofstream ini(output_file);

    if (!ini) {
        throw std::runtime_error(
            "Could not create OMNeT++ ini file: " +
            output_file.string()
        );
    }

    // ============================================================
    // General simulation configuration
    // ============================================================

    ini << "[General]\n\n";

    ini << "network = WSNSimulation\n";

    ini << "sim-time-limit = 180s\n";

    ini << "seed-set = "
        << network.seed + (seed_counter*10)
        << "\n\n";

    // ============================================================
    // Network size
    //
    // These parameters must exist in WSNSimulation.ned.
    // ============================================================

    ini << "*.numNodes = "
        << num_nodes
        << "\n";

    ini << "*.numRelays = "
        << num_relays
        << "\n\n";

    ini << "*.node[*].mobility.initialZ = 0m\n";
    ini << "*.relay[*].mobility.initialZ = 0m\n";
    ini << "*.sink.mobility.initialZ = 0m\n";

    // ============================================================
    // Wireless medium
    // ============================================================

    ini << "# Wireless propagation model\n";

    ini << "*.radioMedium.pathLoss.typename = \""
        << getPropagationName(propagation)
        << "\"\n\n";
 
        
    // ============================================================
    // Node interface
    // ============================================================

    ini << "# Sensor node radio\n";

    ini << "*.node[*].wlan[0].typename = \""
        << getInterfaceName(network.interface.at(NodeType::Node))
        << "\"\n";

    ini << "*.node[*].wlan[0].radio.centerFrequency = "
        << network.frequency.at(NodeType::Node)
        << "Hz\n";

    ini << "*.node[*].wlan[0].radio.bandwidth = "
        << network.bandwidth.at(NodeType::Node)
        << "Hz\n";

    ini << "*.node[*].wlan[0].radio.*.bitrate = "
        << network.bitrate.at(NodeType::Node)
        << "bps\n";

    ini << "*.node[*].wlan[0].mac.bitrate = "
        << network.bitrate.at(NodeType::Node)
        << "bps\n";

    ini << "*.node[*].wlan[0].radio.transmitter.power = "
        << network.power.at(NodeType::Node)
        << "W\n\n";

    // ============================================================
    // Relay interface
    // ============================================================

    ini << "# Relay radio\n";

    ini << "*.relay[*].wlan[0].typename = \""
        << getInterfaceName(network.interface.at(NodeType::Relay))
        << "\"\n";

    ini << "*.relay[*].wlan[0].radio.centerFrequency = "
        << network.frequency.at(NodeType::Relay)
        << "Hz\n";

    ini << "*.relay[*].wlan[0].radio.bandwidth = "
        << network.bandwidth.at(NodeType::Relay)
        << "Hz\n";

    ini << "*.relay[*].wlan[0].radio.*.bitrate = "
        << network.bitrate.at(NodeType::Relay)
        << "bps\n";

    ini << "*.relay[*].wlan[0].mac.bitrate = "
        << network.bitrate.at(NodeType::Relay)
        << "bps\n";

    ini << "*.relay[*].wlan[0].radio.transmitter.power = "
        << network.power.at(NodeType::Relay)
        << "W\n\n";

    // ============================================================
    // Sink interface
    // ============================================================

    ini << "# Sink radio\n";

    ini << "*.sink.wlan[0].typename = \""
        << getInterfaceName(network.interface.at(NodeType::Relay))
        << "\"\n";

    ini << "*.sink.wlan[0].radio.centerFrequency = "
        << network.frequency.at(NodeType::Relay)
        << "Hz\n";

    ini << "*.sink.wlan[0].radio.bandwidth = "
        << network.bandwidth.at(NodeType::Relay)
        << "Hz\n";

    ini << "*.sink.wlan[0].radio.*.bitrate = "
        << network.bitrate.at(NodeType::Relay)
        << "bps\n";

    ini << "*.sink.wlan[0].mac.bitrate = "
        << network.bitrate.at(NodeType::Relay)
        << "bps\n";
    /*
     * The receiver can transmit IEEE 802.15.4 ACKs, so its
     * transmission power is configured as well.
     */
    ini << "*.sink.wlan[0].radio.transmitter.power = "
        << network.power.at(NodeType::Relay)
        << "W\n\n";

    // ============================================================
    // Traffic generator
    // ============================================================

    ini << "# Traffic\n";

    ini << "*.node[*].numApps = 1\n";
 
    ini << "*.node[*].app[0].typename = \""
        << getTrafficName(network.traffic.at(NodeType::Node))
        << "\"\n";

    ini << "*.node[*].app[0].destAddresses = \"sink\"\n";
    ini << "*.node[*].app[0].destPort = 5000\n";

    ini << "*.node[*].app[0].messageLength = "
        << network.packet_length
        << "B\n";

    ini << "*.node[*].app[0].sendInterval = "
        << network.interval
        << "s\n";

    ini << "*.node[*].app[0].startTime = 1s\n\n";

    ini << "*.relay[*].numApps = 0\n";

    ini << "*.sink.numApps = 1\n";
    ini << "*.sink.app[0].typename = \"UdpSink\"\n";
    ini << "*.sink.app[0].localPort = 5000\n\n";

    // ============================================================
    // Mobility
    // ============================================================

    ini << "# Static node positions\n";

    ini << "*.node[*].mobility.typename = \"StationaryMobility\"\n";
    ini << "*.node[*].mobility.initFromDisplayString = false\n";

    ini << "*.relay[*].mobility.typename = \"StationaryMobility\"\n";
    ini << "*.relay[*].mobility.initFromDisplayString = false\n";

    ini << "*.sink.mobility.typename = \"StationaryMobility\"\n";
    ini << "*.sink.mobility.initFromDisplayString = false\n\n";

    // ============================================================
    // Routing
    // ============================================================

    ini << "# IPv4 routing\n";

    // Sensor nodes generate traffic but must NOT be used as routers.
    ini << "*.node[*].forwarding = false\n";

    // Relays are the only intermediate forwarding nodes.
    ini << "*.relay[*].forwarding = true\n";

    // Sink is only a destination.
    ini << "*.sink.forwarding = false\n\n";

    // Let INET assign IP addresses and calculate static routes.
    //
    // IMPORTANT: errorRate is used instead of hopCount because this
    // is a wireless network. A direct wireless link may exist
    // topologically but have an unusable packet error rate.
    ini << "*.configurator.config = xml(\""
       "<config>"
       "<interface hosts='**' "
       "address='10.0.0.x' "
       "netmask='255.255.255.0'/>"
       "<autoroute metric='errorRate'/>"
       "</config>"
       "\")\n";

    ini << "*.configurator.optimizeRoutes = false\n\n";

    // ============================================================
    // Address resolution
    // ============================================================

    ini << "**.arp.typename = \"GlobalArp\"\n\n";


    // ============================================================
    // Results
    // ============================================================

    ini << "# Store scalars, avoid large vector result files\n";
    ini << "**.scalar-recording = true\n";
    ini << "**.vector-recording = false\n";

    ini << "output-scalar-file = network/simulation_results.sca\n";

    ++seed_counter;
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

    if (values.size() != 16) {
        throw std::runtime_error(
            "Invalid network configuration. Expected 16 fields, got " +
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

    network.traffic[NodeType::Relay] =
        std::stoul(values[5]);


    // ============================================================
    // Sensor/node configuration
    // ============================================================

    network.interface[NodeType::Node] =
        std::stoul(values[6]);

    network.frequency[NodeType::Node] =
        std::stod(values[7]);

    network.bandwidth[NodeType::Node] =
        std::stod(values[8]);

    network.bitrate[NodeType::Node] =
        std::stod(values[9]);

    network.power[NodeType::Node] =
        std::stod(values[10]);

    network.traffic[NodeType::Node] =
        std::stoul(values[11]);


    // ============================================================
    // Shared network parameters
    // ============================================================

    network.propagation = std::stoul(values[12]);

    network.packet_length =
        std::stoul(values[13]);

    network.interval =
        std::stod(values[14]);

    network.seed =
        std::stoul(values[15]);

    return network;
}

double readScalar(const std::string& filename, const std::string& scalarName) {
    std::ifstream file(filename);

    if (!file.is_open()) {
        throw std::runtime_error(
            "Could not open scalar file: " + filename
        );
    }

    std::string line;

    while (std::getline(file, line)) {
        if (line.rfind("scalar", 0) != 0)
            continue;

        std::istringstream iss(line);

        std::string type;
        std::string module;
        std::string name;
        double value;

        iss >> type
            >> std::quoted(module)
            >> std::quoted(name)
            >> value;

        if (name == scalarName) {
            return value;
        }
    }

    throw std::runtime_error(
        "Scalar not found: " + scalarName
    );
}