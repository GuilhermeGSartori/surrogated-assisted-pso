#include "pso.h"

#include <iostream>
#include <vector>
#include <limits>
#include <random>
#include <algorithm>


Swarm::Swarm(std::size_t n_particles, std::size_t n_relays, Coordinates sink) : n_particles(n_particles), n_relays(n_relays), global_best(n_relays) {
    particles.reserve(n_particles);

    this->sink = sink;

    for (std::size_t i = 0; i < n_particles; ++i) {
        particles.emplace_back(n_relays);
    }
}

void Swarm::updateGlobalBest(const Solution& candidate) {
    if (candidate.fitness > global_best.fitness) {
        global_best = candidate;
    }
}

void Swarm::setRanges(double relay_range, double node_range) {
    this->relay_range = relay_range;
    this->node_range = node_range;
}

void Swarm::setWeights(double w, double c1, double c2) {
    //weights = Weights(w, c1, c2, r1, r2);
    weights.w = w;
    weights.c1 = c1;
    weights.c2 = c2;
}

void Swarm::initRelays(const Dimensions& area, std::mt19937& rng) {

    for (auto& p: particles) {
        do {
            LHS(p.getPositions(), n_relays, area, rng);
        } while (!isConnected(p.getPositions(), sink, relay_range));

        for (auto& v: p.getVelocities()) {
            v.x = 0;
            v.y = 0;
        }
    }
    // escrever em arquivo as posicoes inicieis de todas as particulas
}

bool Particle::compareBest(const double fitness) { // pq aqui PRECISA retornar referenica?

    if (fitness > personal_best.fitness) {
        personal_best.relay_positions = relay_positions;
        personal_best.fitness = fitness;

        return true;
    }

    return false;
}

void Particle::calculateVelocity(Weights weights, const Solution& global_best, std::mt19937& rng) {

    std::uniform_real_distribution<double> dist(0.0, 1.0);

    auto personal_bias = (personal_best.relay_positions - relay_positions) * weights.c1;
    auto global_bias = (global_best.relay_positions - relay_positions) * weights.c2;

    for (std::size_t i = 0; i < relay_positions.size(); ++i) {
        double r1 = dist(rng);
        double r2 = dist(rng);
        personal_bias[i].x = personal_bias[i].x * r1;
        personal_bias[i].y = personal_bias[i].y* r2;
        r1 = dist(rng);
        r2 = dist(rng);
        global_bias[i].x = global_bias[i].x * r1;
        global_bias[i].y = global_bias[i].y * r2;
    }

    relay_velocities = relay_velocities * weights.w + personal_bias + global_bias;
}

void Particle::updatePositions(const Dimensions& area) {
    relay_positions += relay_velocities;

    for (std::size_t i = 0; i < relay_positions.size(); ++i) {

        double old_x = relay_positions[i].x;
        double old_y = relay_positions[i].y;

        relay_positions[i].x =
            std::clamp(old_x, 0.0, area.width);

        relay_positions[i].y =
            std::clamp(old_y, 0.0, area.height);

        if (relay_positions[i].x != old_x) {
            relay_velocities[i].x = 0.0;
        }

        if (relay_positions[i].y != old_y) {
            relay_velocities[i].y = 0.0;
        }
    }
}

void evaluateSolution(Swarm& swarm, const Scenario& scenario) {
    for (auto& p: swarm.getParticles()) {
        double fitness;
        if (scenario.backend == Method::Simulation) {
            // Simulador
            fitness = 0;
        }
        else {
            fitness = 0;
        }
        if (p.compareBest(fitness))
            swarm.updateGlobalBest(p.getPersonalBest());
    }
}

int pso(Swarm& swarm, const Scenario& scenario, std::mt19937& rng) {

    int iterations = 0;

    do
    {
        evaluateSolution(swarm, scenario);

        for (auto& p: swarm.getParticles()) {
            p.calculateVelocity(swarm.getWeights(), swarm.getGlobalBest(), rng);
            p.updatePositions(scenario.area);
        }
    } while (++iterations < iterations_max);

    evaluateSolution(swarm, scenario);  

    
    // aqui só escreve as posicoes mesmo
    // escreve em artigo de config? chama serviço? como vai ser o backend.. escreve em arquivo e invoca processo ou integração c++?
    // chama por linha de comando? como faz? roda, espera, vê saida??? como vai ser integração
    // evaluation backend ==> serviiço ou chamar simulacao

}

template <typename Container>
bool isConnected(const Container& nodes, const Coordinates& sink, double relay_range) {

    std::size_t n = nodes.size();

    std::vector<bool> visited(n, false);
    std::queue<std::size_t> queue;

    double range_sq = relay_range*relay_range;

    for (std::size_t i = 0; i < n; ++i) {
        if (distanceSquared(nodes[i], sink) <= range_sq) {
            visited[i] = true;
            queue.push(i);
        }
    }

    while (!queue.empty()) {
        const std::size_t current = queue.front();
        queue.pop();

        for (std::size_t i = 0; i < n; ++i) {
            if (visited[i])
                continue;
            else if (distanceSquared(nodes[current], nodes[i]) <= range_sq) {
                visited[i] = true;
                queue.push(i);
            }
        }

    }

    for (bool connected : visited) {
        if (!connected) 
            return false;
    }

    return true;
}