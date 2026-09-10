#include <fstream>
#include <iostream>
#include <string_view>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>

#include "pso.h"
#include "app.h"
#include "trainer.h"

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

    std::ofstream final_log("logs/final_log.log");

    final_log << "Area: "
        << scenario.area.width << " x "
        << scenario.area.height << '\n';

    final_log << "Nodes Positions: \n";
    logNodes(final_log, scenario);

    final_log << "First Relays:\n";
    swarm.logFirstRelay(final_log);

    std::ofstream log = createLogFile();

    auto start = std::chrono::steady_clock::now();
    const Solution& global_best = pso(swarm, scenario, rng, log);
    auto end = std::chrono::steady_clock::now();

    std::chrono::duration<double> elapsed = end - start;
    
    std::cout << "Final Evaluation Time: " << elapsed.count() << " seconds\n";

    log << "Final global best fitness: " << global_best.fitness << "\n";
    log << "Final global best relays:\n";
    final_log << "Final global best relays:\n";
    
    for (const auto& pos: global_best.relay_positions) {
        log << pos.x << ", " << pos.y << '\n';
        final_log << pos.x << ", " << pos.y << '\n';
    }    
    return 0;
}

int main(int argc, char* argv[]) {

    if (argc == 3) {
        std::string_view mode = argv[1];
        if (mode == "training") {
            Scenario scenario = parseScenario(argv[2]);
            generateDataset(scenario);

            return 0;
        }

        return 1;
    }
    else if (argc < 4) {
        std::cerr << "Missing optimizer mode, scenario or method\n";
        return 1;
    }
    else {
        std::string_view mode = argv[1];

        auto it = optimizers.find(mode);

        if (it == optimizers.end()) {
            std::cerr << "Unknown optimizer: " << mode << '\n';
            return 1;
        }

        Scenario scenario = parseScenario(argv[2]);
        scenario.backend = parseMethod(argv[3]);

        configNetwork(scenario);

        return it->second(argc, argv, scenario);
    }
}
