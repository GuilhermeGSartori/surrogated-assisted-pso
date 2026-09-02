// to do:
// -- PSO implementation -- Gerar dados do pacote, definir arquivo config, integrar com omnet
// -- tests

#include <fstream>
#include <iostream>
#include <string_view>
#include <algorithm>
#include <numeric>
#include <random>
#include "pso.h"
#include "app.h"

int initPso(int argc, char* argv[], Scenario& scenario) {
    if (argc != 8) {
        std::cerr << "Usage: ./surrogated-assisted-optimizer pso <scenario> <method> <particles> <w> <c1> <c2>\n";
        return 1;
    }

    const std::size_t n_particles = std::stoul(argv[4]);
    const double w = std::stod(argv[5]);
    const double c1 = std::stod(argv[6]);
    const double c2 = std::stod(argv[7]);

    Swarm swarm(n_particles, scenario.n_relays, scenario.sink);

    swarm.setRanges(
        scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay}),
        scenario.network.simulated_range.at({NodeType::Node, NodeType::Relay})
    );

    std::mt19937 rng(scenario.seed);

    swarm.setWeights(w, c1, c2);

    LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);

    writeNodePositions(scenario.nodes, scenario.sink, "network/sensor_nodes.ini");
    
    swarm.initRelays(scenario.area, rng); 

    // Area baseada em PA, tamnho de pacote baseado no tipo de dado q iria (pacote pequeno com alguns bytes)

    // TENHO QUE COLOCAR QUE RODEI SUDO APT INSTALL CMAKE NA VM!!!

    std::ofstream log = createLogFile();

    const Solution& global_best = pso(swarm, scenario, rng, log);
    log << "Final global best fitness: " << global_best.fitness << "\n";
    log << "Final global best relays: ";
    for (const auto& pos: global_best.relay_positions) {
        log << pos.x << ", " << pos.y << '\n';
    }    
    return 0;
}

int main(int argc, char* argv[]) {

    if (argc < 4) {
        std::cerr << "Missing optimizer mode, scenario or method\n";
        return 1;
    }

    std::string_view mode = argv[1];

    auto it = optimizers.find(mode);

    if (it == optimizers.end()) {
        std::cerr << "Unknown optimizer: " << mode << '\n';
        return 1;
    }

    Scenario scenario = parseScenario(argv[2]);
    scenario.backend = parseMethod(argv[3]);

    configNetwork(scenario);

    return 0;
    //return it->second(argc, argv, scenario);
}