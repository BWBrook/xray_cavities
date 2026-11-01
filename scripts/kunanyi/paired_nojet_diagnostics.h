#ifndef PAIRED_NOJET_DIAGNOSTICS_H
#define PAIRED_NOJET_DIAGNOSTICS_H

#include "pluto.h"

void PairedNojetAccumulateBoundaryFlux(const Sweep *, int, int, double, Grid *);
void PairedNojetAccumulateGravityWork(double, double);
void PairedNojetBeginConversionEnergyRepair(double, Grid *);
void PairedNojetRecordConversionEnergyRepairCell(double, int, uint16_t);
void PairedNojetEndConversionEnergyRepair(int);
void PairedNojetAnalysis(const Data *, Grid *);

#endif
