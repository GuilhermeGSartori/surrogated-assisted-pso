// to do:
// -- tests
// -- Omnet integration
// -- PSO implementation -- validar que tenho tudo q preciso
//      -- salvar infos em arquivos... posicoes, velocidades iniciais, log, etc... salvar TUDO...
//      -- tamanho do pacote, tempo de geracao de cada nodo...
//      -- escrever TUDO...
//      -- e colocar o conreduo em arquivo de config para omnet

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

    LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng); // vai preencher as posicoes de nodo inicial => latin hyper cube para preencher as posicoes do swarm
    swarm.initRelays(scenario.area, rng); 

    // baseado em numero de nodos, criar packet size max e packet timeout...
    // Pacote acho que vai ser sempre igual.. temperatura, umidade, lumens... 6 bytes...? timestamp, posicao...
    // tamanho do pacote definido claramente... tempo de geracao eu criar aqui....
    // com funcao auxiliar tendo maximo e minimo e distribuir nesse range..


    // escrever as posicoes em todos os lugares e nodos em arquivo

    /// Escrever tudo q tem no scenario no arquivo com timestamp de nome

    // o q preciso pra rodar? posicoes nodos, posicoes relays, w, c1, c2, sink, ranges, configm rede, velocidade inicial, ...?

    // sortear valor random de tamanho de pacote e tempo para geração para cada nodo e escrever no arquivo de config
    pso(swarm, scenario, rng);

    // pegar resultados e plottar e sei lá... e csv ==> acho que nao, vou jogar tudo no meu log e depois façi um script só pra plottar

    // ideia é ambiente sem nas proporcoes de PA real, nodos Latin Hypercube para cobrir area e simular PA real..?
    // quantidade por área e tamanho area
    

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