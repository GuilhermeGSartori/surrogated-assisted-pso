#pragma once

#include <iostream>
#include <vector>
#include <limits>
#include <random>
#include "aux.h"

#define iterations_max 100

struct Weights {
    double w = 0.0;
    double c1 = 0.0;
    double c2 = 0.0;
};

struct Solution {
    FixedSizeVector<Coordinates> relay_positions;
    double fitness = std::numeric_limits<double>::lowest();

    explicit Solution(std::size_t n_relays)
        : relay_positions(n_relays)
    {}
};

class Particle {
private:
    FixedSizeVector<Coordinates> relay_positions;
    FixedSizeVector<Coordinates> relay_velocities;
    Solution personal_best;
    double current_fitness = 0.0;

public:
    explicit Particle(std::size_t n_relays) : relay_positions(n_relays), relay_velocities(n_relays), personal_best(n_relays) {}

    bool compareBest(const double fitness);

    const Solution& getPersonalBest() const {
        return personal_best;
    }

    FixedSizeVector<Coordinates>& getBestPositions() {
        return personal_best.relay_positions;
    }

    const FixedSizeVector<Coordinates>& getBestPositions() const {
        return personal_best.relay_positions;
    }

    FixedSizeVector<Coordinates>& getPositions() {
        return relay_positions;
    }

    const FixedSizeVector<Coordinates>& getPositions() const {
        return relay_positions;
    }

    FixedSizeVector<Coordinates>& getVelocities() {
        return relay_velocities;
    }

    const FixedSizeVector<Coordinates>& getVelocities() const {
        return relay_velocities;
    }

    void calculateVelocity(Weights weights, const Solution& global_best, std::mt19937& rng);

    void updatePositions(const Dimensions& area);
};

class Swarm {
private:
    std::vector<Particle> particles;
    size_t n_particles;
    size_t n_relays;
    Weights weights;
    Solution global_best;
    Coordinates sink;

    double node_range;
    double relay_range;

public:
    Swarm(std::size_t n_particles, std::size_t n_relays, Coordinates sink);
    
    std::vector<Particle>& getParticles() {
        return particles;
    }

    const std::vector<Particle>& getParticles() const {
        return particles;
    }

    const std::size_t getN_relays() const {
        return n_relays;
    }

    const std::size_t getN_particles() const {
        return n_particles;
    }

    const Solution& getGlobalBest() const {
        return global_best;
    }

    Weights getWeights() { return weights; }

    const Weights getWeights() const { return weights; }

    void updateGlobalBest(const Solution& candidate);

    void initRelays(const Dimensions& area, std::mt19937& rng);

    void setRanges(double relay_range, double node_range);
    
    void setWeights(double w, double c1, double c2);
};

void evaluateSolution(Swarm& swarm, const Scenario& scenario) ;

int pso(Swarm& swarm, const Scenario& scenario, std::mt19937& rng);

void logHeader(std::ofstream& log, const Swarm& swarm, const Scenario& scenario);

template <typename Container>
bool isConnected(const Container& nodes, const Coordinates& sink, double relay_range);