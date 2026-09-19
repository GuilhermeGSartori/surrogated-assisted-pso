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
#include "surrogate_client.h"

int initPso(int argc, char* argv[], Scenario& scenario) {

    std::cout << "PSO!\n";
    
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
    
    log << "Final Evaluation Time: " << elapsed.count() << " seconds\n";

    log << "Final global best fitness: " << global_best.fitness << "\n";
    std::cout << "Final global best fitness: " << global_best.fitness << "\n";
    log << "Final global best relays:\n";
    final_log << "Final global best relays:\n";
    
    for (const auto& pos: global_best.relay_positions) {
        log << pos.x << ", " << pos.y << '\n';
        final_log << pos.x << ", " << pos.y << '\n';
    }    
    return 0;
}

int initLHSHeuristic(int argc, char* argv[], Scenario& scenario) {

    if (argc != 5) {
        std::cerr << "Usage: ./surrogated-assisted-optimizer lhs <scenario> <method> <n_iterations>\n";
        return 1;
    }

    const double range = scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay});

    const unsigned int n_iterations = static_cast<unsigned int>(std::stoul(argv[4]));

    std::mt19937 rng(scenario.seed);

    LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);

    writeNodePositions(scenario.nodes, scenario.sink, "network/sensor_nodes.ini");

    FixedSizeVector<Coordinates> relays(scenario.n_relays);
    FixedSizeVector<Coordinates> best_relays(scenario.n_relays);

    constexpr int MAX_RETRIES = 1000;
    double best_fitness = -std::numeric_limits<double>::infinity();

    std::ofstream log = createLogFile();
    std::ofstream final_log("logs/final_log.log");

    final_log << "Area: "
        << scenario.area.width << " x "
        << scenario.area.height << '\n';

    final_log << "Nodes Positions: \n";
    logNodes(final_log, scenario);

    auto start = std::chrono::steady_clock::now();
    for (unsigned int i = 0; i < n_iterations; ++i) {

        int retries = 0;

        do {
            LHS(relays, scenario.n_relays, scenario.area, rng);

            ++retries;

        } while (!isConnected(relays, scenario.sink, range) && retries < MAX_RETRIES);

        if (!isConnected(relays, scenario.sink, range)) {

            while (!isConnected(relays, scenario.sink, range)) {
                for (auto& relay : relays) {
                    relay.x = scenario.sink.x + 0.9 * (relay.x - scenario.sink.x);

                    relay.y = scenario.sink.y + 0.9 * (relay.y - scenario.sink.y);
                }
            }
        }

        double fitness = 0.0;
        if (scenario.backend == Method::Simulation) {
            fitness = runSimulation(relays, scenario);
        }
        else if (scenario.backend == Method::Surrogate) {
            std::string packet = generatePacket(relays, scenario);
            
            appendNodes(scenario.nodes, packet, scenario.n_clusters);
            bool connected = isConnected(relays, scenario.sink, scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay}));
            
            if (connected)
            	fitness = sendPacket(packet);
            else
            	fitness = 0.0;
            
            if (fitness == -1.0) {
                std::cout << "Error\n";
            }
        }

        if (fitness > best_fitness) {
            best_fitness = fitness;
            best_relays = relays;
            log << "ITERATION: " << i << "\n";
            log << "new best fitness: " << best_fitness << "\n";
        }
    }
    auto end = std::chrono::steady_clock::now();

    std::chrono::duration<double> elapsed = end - start;
    
    std::cout << "Final Evaluation Time: " << elapsed.count() << " seconds\n";
    
    log << "Final Evaluation Time: " << elapsed.count() << " seconds\n";

    double final_fitness = runSimulation(best_relays, scenario);
    log << "Final global best fitness: " << final_fitness << "\n";
    std::cout << "Final global best fitness: " << final_fitness << "\n";
    log << "Final global best relays:\n";
    final_log << "Final global best relays:\n";
    
    for (const auto& pos: best_relays) {
        log << pos.x << ", " << pos.y << '\n';
        final_log << pos.x << ", " << pos.y << '\n';
    }    
    return 0;
}

int initNaive(int argc, char* argv[], Scenario& scenario) {

    std::cout << "Naive!\n";

    if (argc != 5) {
        std::cerr << "Usage: ./surrogated-assisted-optimizer naive <scenario> <method> <n_iterations>\n";
        return 1;
    }

    const double range = scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay});

    const unsigned int n_iterations = static_cast<unsigned int>(std::stoul(argv[4]));

    std::mt19937 rng(scenario.seed);

    LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);

    writeNodePositions(scenario.nodes, scenario.sink, "network/sensor_nodes.ini");

    FixedSizeVector<Coordinates> relays(scenario.n_relays);
    FixedSizeVector<Coordinates> best_relays(scenario.n_relays);

    double best_fitness = -std::numeric_limits<double>::infinity();

    std::ofstream log = createLogFile();
    std::ofstream final_log("logs/final_log.log");

    final_log << "Area: "
        << scenario.area.width << " x "
        << scenario.area.height << '\n';

    final_log << "Nodes Positions: \n";
    logNodes(final_log, scenario);

    std::uniform_real_distribution<double> x_dist(0.0, scenario.area.width);
    std::uniform_real_distribution<double> y_dist(0.0, scenario.area.height);
    constexpr unsigned int MAX_RETRIES = 100000;

    auto start = std::chrono::steady_clock::now();
    for (unsigned int i = 0; i < n_iterations; ++i) {

        unsigned int retries = 0;

        do {
            for (auto& relay : relays) {
                relay.x = x_dist(rng);
                relay.y = y_dist(rng);
            }

            ++retries;

        } while (!isConnected(relays, scenario.sink, range) &&  retries < MAX_RETRIES);

        if (!isConnected(relays, scenario.sink, range)) {
            std::cerr << "Could not generate connected random solution\n";
            return 1;
        }
        
        double fitness = 0.0;
        if (scenario.backend == Method::Simulation) {
            fitness = runSimulation(relays, scenario);
        }
        else if (scenario.backend == Method::Surrogate) {
            std::string packet = generatePacket(relays, scenario);
            
            appendNodes(scenario.nodes, packet, scenario.n_clusters);
            fitness = sendPacket(packet);

            if (fitness == -1.0) {
                std::cout << "Error\n";
            }
        }

        if (fitness > best_fitness) {
            best_fitness = fitness;
            best_relays = relays;
            log << "ITERATION: " << i << "\n";
            log << "new best fitness: " << best_fitness << "\n";
        }
    }
    auto end = std::chrono::steady_clock::now();

    std::chrono::duration<double> elapsed = end - start;
    
    std::cout << "Final Evaluation Time: " << elapsed.count() << " seconds\n";
    
    log << "Final Evaluation Time: " << elapsed.count() << " seconds\n";

    double final_fitness = runSimulation(best_relays, scenario);
    log << "Final global best fitness: " << final_fitness << "\n";
    std::cout << "Final global best fitness: " << final_fitness << "\n";
    log << "Final global best relays:\n";
    final_log << "Final global best relays:\n";
    
    for (const auto& pos: best_relays) {
        log << pos.x << ", " << pos.y << '\n';
        final_log << pos.x << ", " << pos.y << '\n';
    }    
    return 0;
}

int main(int argc, char* argv[]) {

    if (argc == 3) {
        std::string_view mode = argv[1];
        if (mode == "training") {
            TrainingScenario scenario = parseTrainingScenario(argv[2]);
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

        std::cout << ">>>\n";
        std::cout << "Scenario seed: " << scenario.seed << "\n";
        std::cout << "Scenario area: " << scenario.area.height << "\n";
        std::cout << "Num relays: " << scenario.n_relays << "\n";
        scenario.backend = parseMethod(argv[3]);

        configNetwork(scenario);

        return it->second(argc, argv, scenario);
    }
}
