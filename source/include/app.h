#pragma once

#include <unordered_map>
#include "pso.h"
#include "aux.h"
#include "network_files.h"

using OptimizerFunction = int (*)(int, char*[], Scenario&);

int initPso(int argc, char* argv[], Scenario& scenario);
int initLHSHeuristic(int argc, char* argv[], Scenario& scenario);
int initNaive(int argc, char* argv[], Scenario& scenario);

const std::unordered_map<std::string_view, OptimizerFunction> optimizers = {
    {"pso", initPso},
    {"lhs", initLHSHeuristic},
    {"naive", initNaive}
};