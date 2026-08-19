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
        std::cerr << "Usage: ./optimizer pso <method> <scenario> <particles> <w> <c1> <c2>\n";
        return 1;
    }

    const std::size_t n_particles = std::stoul(argv[4]);
    const double w = std::stod(argv[5]);
    const double c1 = std::stod(argv[6]);
    const double c2 = std::stod(argv[7]);

    Swarm swarm(n_particles, scenario.n_relays, scenario.sink);
    swarm.setRanges(scenario.relay_range, scenario.node_range);

    std::mt19937 rng(scenario.seed);

    swarm.setWeights(w, c1, c2);

    LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);
    swarm.initRelays(scenario.area, rng); 

    // baseado em numero de nodos, criar packet size max e packet timeout...
    // Pacote acho que vai ser sempre igual.. temperatura, umidade, lumens... 6 bytes...? timestamp, posicao...
    // tamanho do pacote definido claramente... tempo de geracao eu criar aqui....
    // com funcao auxiliar tendo maximo e minimo e distribuir nesse range..

    // o q preciso pra rodar? configm rede
    // sortear valor random de tamanho de pacote e tempo para geração para cada nodo e escrever no arquivo de config

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

    return it->second(argc, argv, scenario);
}