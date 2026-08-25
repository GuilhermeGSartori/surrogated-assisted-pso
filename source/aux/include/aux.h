#pragma once

#include <map>
#include <unordered_map>
#include <utility>
#include <cstddef>
#include <string>
#include <vector>
#include <stdexcept>
#include <string_view>

template <typename T>
class FixedSizeVector {
private:
    std::vector<T> vec;
    void checkSameSize(const FixedSizeVector& other) const;

public:
    explicit FixedSizeVector(std::size_t size)
        : vec(size)
    {
    }

    T& operator[](std::size_t index) {
        return vec[index];
    }

    const T& operator[](std::size_t index) const {
        return vec[index];
    }

    T& at(std::size_t index) {
        return vec.at(index);
    }

    const T& at(std::size_t index) const {
        return vec.at(index);
    }

    std::size_t size() const {
        return vec.size();
    }

    auto begin() {
        return vec.begin();
    }

    auto end() {
        return vec.end();
    }

    auto begin() const {
        return vec.begin();
    }

    auto end() const {
        return vec.end();
    }
    
    FixedSizeVector& operator=(const FixedSizeVector& other)
    {
        checkSameSize(other);
        std::copy(other.vec.begin(), other.vec.end(), vec.begin());

        return *this;
    }
        
    FixedSizeVector& operator=(FixedSizeVector&& other)
    {
        checkSameSize(other);

        for (std::size_t i = 0; i < vec.size(); ++i) {
            vec[i] = std::move(other.vec[i]);
        }

        return *this;
    }

    FixedSizeVector& operator+=(const FixedSizeVector& other)
    {
        checkSameSize(other);
        for (std::size_t i = 0; i < size(); ++i) {
            vec[i] += other.vec[i];
        }

        return *this;
    }

    FixedSizeVector operator+(const FixedSizeVector& other) const
    {
        checkSameSize(other);
        FixedSizeVector result(size());

        for (std::size_t i = 0; i < size(); ++i) {
            result[i] = vec[i] + other[i];
        }

        return result;
    }

    FixedSizeVector operator-(const FixedSizeVector& other) const
    {
        checkSameSize(other);
        FixedSizeVector result(size());

        for (std::size_t i = 0; i < size(); ++i) {
            result[i] = vec[i] - other[i];
        }

        return result;
    }

    FixedSizeVector operator*(double scalar) const
    {
        FixedSizeVector result(size());

        for (std::size_t i = 0; i < size(); ++i) {
            result[i] = vec[i] * scalar;
        }

        return result;
    }

    // Prevent changing size through assignment
    FixedSizeVector& operator=(const FixedSizeVector&) = delete;
    FixedSizeVector& operator=(FixedSizeVector&&) = delete;
};

struct Coordinates {
    double x = 0.0;
    double y = 0.0;


    Coordinates& operator+=(const Coordinates& other) {
        x += other.x;
        y += other.y;
        return *this;
    }

    Coordinates operator+(const Coordinates& other) const {
        return {x + other.x, y + other.y};
    }

    Coordinates operator-(const Coordinates& other) const {
        return {x - other.x, y - other.y};
    }

    Coordinates operator*(double scalar) const {
        return {x * scalar, y * scalar};
    }

    double distanceSquared(const Coordinates& a, const Coordinates& b);
};

struct Dimensions {
    double width = 0.0;
    double height = 0.0;
};

enum class Method {
    Simulation,
    Surrogate,
    Hybrid
};

constexpr std::string_view toString(Method method);

struct Scenario {
    std::size_t n_relays = 0;
    unsigned int seed = 0;
    std::size_t n_nodes = 0;

    Dimensions area;

    std::size_t n_clusters = 0;

    Coordinates sink;

    std::vector<Coordinates> nodes;

    Method backend;

    std::vector<int> packet_timeouts;

    unsigned int network_config;

    Network network;
};

void configNetwork(Scenario& scenario);

void writeNodePositions(const std::vector<Coordinates>& nodes, const std::filesystem::path& output_file);

void writeRelayPositions(const FixedSizeVector<Coordinates>& relays, const std::filesystem::path& output_file);

Method parseMethod(const std::string& method);

Scenario parseScenario(const std::string& filename);

std::ofstream createLogFile();

double runSimulation(const FixedSizeVector<Coordinates>& relays, const Scenario& scenario);

template <typename Container>
void LHS(Container& nodes, std::size_t n, const Dimensions& area, std::mt19937& rng);