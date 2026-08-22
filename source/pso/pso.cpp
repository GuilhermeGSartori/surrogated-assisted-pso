#include "pso.h"

#include <fstream>
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

bool Swarm::updateGlobalBest(const Solution& candidate) {
    if (candidate.fitness > global_best.fitness) {
        global_best = candidate;
        
        return true;
    }
    return false;
}

void Swarm::setRanges(double relay_range, double node_range) {
    this->relay_range = relay_range;
    this->node_range = node_range;
}

void Swarm::setWeights(double w, double c1, double c2) {
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

void evaluateSolution(Swarm& swarm, const Scenario& scenario, std::ofstream& log) {
    int particle = 1;

    for (auto& p: swarm.getParticles()) {
        log << "-------------\n"
            << "Particle: " << particle << ":\n"
            << "Relays Coordinates:\n";

        for (const auto& pos: p.getPositions()) {
            log << pos.x << ", " << pos.y << '\n';
        }
        
        double fitness;
        if (scenario.backend == Method::Simulation) {
            fitness = runSimulation(p.getPositions(), scenario);
        }
        else {
            fitness = 0;
        }
        
        log << "Resulting Fitness: " << fitness << "\n";

        if (p.compareBest(fitness)) {
            log << "New local best!\n";
            if (swarm.updateGlobalBest(p.getPersonalBest()))
                log << "New global best!\n";
        }

        ++particle;
    }
}

const Solution& pso(Swarm& swarm, const Scenario& scenario, std::mt19937& rng, std::ofstream& log) {

    int iterations = 0;

    logHeader(log, swarm, scenario);

    do
    {
        log << "-- ITERATION " << iterations << " --\n";
        evaluateSolution(swarm, scenario, log);

        const Solution& global_best = swarm.getGlobalBest();

        log << "Current global best fitness: " << global_best.fitness << "\n";
        log << "Current global best relays: ";

        for (const auto& pos: global_best.relay_positions) {
            log << pos.x << ", " << pos.y << '\n';
        }

        int particle = 1;
        for (auto& p: swarm.getParticles()) {
            p.calculateVelocity(swarm.getWeights(), swarm.getGlobalBest(), rng);
            const FixedSizeVector<Coordinates>& velocities = p.getVelocities();
            log << "Particle " << particle << " new velocities: ";
            for (const auto& pos: velocities) {
                log << pos.x << ", " << pos.y << '\n';
            }           
            p.updatePositions(scenario.area);

            ++particle;
        }
    } while (++iterations < iterations_max);

    log << "-- ITERATION " << iterations << " --\n";
    evaluateSolution(swarm, scenario, log);

    return swarm.getGlobalBest();
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

void logHeader(std::ofstream& log, const Swarm& swarm, const Scenario& scenario) {

    log << "PSO EXECUTION\n";
    log << "============================\n";

    log << "Seed: " << scenario.seed << '\n';
    log << "Particles: " << swarm.getN_particles() << '\n';
    log << "Relays: " << scenario.n_relays << '\n';
    log << "Iterations: " << iterations_max << '\n';

    log << "Backend: " << toString(scenario.backend) << '\n';

    log << "Network Configuration: " << scenario.network_config << '\n';

    log << "Area: "
        << scenario.area.width << " x "
        << scenario.area.height << '\n';

    log << "Sink: " << scenario.sink.x << ", " << scenario.sink.y << '\n';

    log << "Simulated Relay range: " << swarm.getRelayRange() << '\n'; // ISSO E IsConnected está errado.. tenho q definir uma rede e ja era
    log << "Simulated Node range: " << swarm.getNodeRange() << '\n'; // VOU TER OUTRAS INFOS CONFIGURADAS VIA INPUT DA REDE.. REDE CONFIGURAVEL.. E DAI DESCOBRE RANGE POR EXPERIMENTO E NAO ONPUT... MAS REDE INPUT

    Weights weights = swarm.getWeights();
    
    log << "w: " << weights.w << '\n';
    log << "c1: " << weights.c1 << '\n';
    log << "c2: " << weights.c2 << '\n';

    log << '\n';

    log << "Relay Nodes Positions: \n";
    logRelayNodes(log, swarm);

    log << "Nodes Positions: \n";
    logNodes(log, scenario);

    log << "All particles start with velocity zero\n";
}

void logRelayNodes(std::ofstream& log, const Swarm& swarm) {
    auto& particles = swarm.getParticles();
    for (size_t i = 0; i < swarm.getN_particles(); ++i) {
        log << "PARTICLE " << i+1 << ": \n";
        for (const auto& pos: particles[i].getPositions()) {
            log << pos.x << ", " << pos.y << '\n';
        }
    }
}

void logNodes(std::ofstream& log, const Scenario& scenario) {
    for (const auto& node : scenario.nodes) {
        log << node.x << ", " << node.y << '\n';
    }
}