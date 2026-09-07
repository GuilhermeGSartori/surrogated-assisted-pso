#pragma once

#include <fstream>

#include "aux.h"

void writeDatasetHeader(std::ofstream& file, std::size_t n_relays);
void writeNodesHeader(std::ofstream& file);
void writeNodesScenario(std::ofstream& file, std::size_t scenario_id, const Scenario& scenario);
void writeDatasetRow(std::ofstream& file, std::size_t id, std::size_t sample_id, const Scenario& scenario, const FixedSizeVector<Coordinates>& relays, double fitness);
void generateDataset(Scenario& scenario);