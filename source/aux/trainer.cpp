#include <random>

#include "trainer.h"

void generateDataset(Scenario& scenario) {

    FixedSizeVector<Coordinates> relays(scenario.n_relays);

    configNetwork(scenario);

    double range = scenario.network.simulated_range.at({NodeType::Relay, NodeType::Relay});

    for (int i = 0; i < 100; ++i) {
        std::mt19937 rng(scenario.seed*i);
        LHS(scenario.nodes, scenario.n_nodes, scenario.area, rng);
        writeNodePositions(scenario.nodes, scenario.sink, "network/sensor_nodes.ini");
        do {
            LHS(relays, scenario.n_relays, scenario.area, rng);
        } while (!isConnected(relays, scenario.sink, range));

        for (int j = 0; j < 20; ++j) {
            double fitness = runSimulation(relays, scenario);
            // perturba posicoes iniciais dos relays
        }

    }

    // salva em arquivo tudo do cenário... Python vai clusterizar
}