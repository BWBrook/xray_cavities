"""Reproduce the radial-flux geometry from cap_reference_fixture.json using Python alone."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys


def measure(fixture):
    axes = [fixture['coordinates_kpc'][d] for d in 'xyz']
    centres = [a['centres'] for a in axes]
    edges = [a['edges'] for a in axes]
    radius = fixture['source_radius_kpc']
    theta = math.radians(fixture['cone_half_angle_deg'])
    omega = 4 * math.pi * (1 - math.cos(theta))
    n_inside = n_tag = n_skin = n_cap = n_side = 0
    cell_flux, face_flux, pointed_flux, side_flux = [], [], [], []
    for i, x in enumerate(centres[0]):
        for j, y in enumerate(centres[1]):
            for k, z in enumerate(centres[2]):
                p = [x, y, z]
                r = math.hypot(*p)
                if r > radius:
                    continue
                n_inside += 1
                donor_marked = math.hypot(x, y) <= abs(z) * math.tan(theta)
                n_tag += int(donor_marked)
                cell = (i, j, k)
                for axis in range(3):
                    index = cell[axis]
                    for sign in (-1, 1):
                        q = p.copy()
                        q[axis] = centres[axis][index + sign]
                        if math.hypot(*q) <= radius:
                            continue
                        n_skin += 1
                        q[axis] = edges[axis][index + (sign > 0)]
                        area = math.prod(edges[d][cell[d]+1] - edges[d][cell[d]] for d in range(3) if d != axis)
                        face = area * sign * q[axis] / math.hypot(*q)**3 / omega
                        if math.hypot(*q[:2]) <= abs(q[2]) * math.tan(theta):
                            pointed_flux.append(face)
                        if donor_marked:
                            n_cap += 1
                            cell_flux.append(area * sign * p[axis] / r**3 / omega)
                            face_flux.append(face)
                            if axis != 2:
                                side_flux.append(face)
                                n_side += 1
    for name, case in fixture['cases'].items():
        factor = case['prescribed_continuum_mass_over_label']
        yield {
            'case': name, 'flagged_cells': n_inside, 'tagged_cells': n_tag, 'all_interfaces': n_skin,
            'cap_interfaces': n_cap, 'lateral_cap_interfaces': n_side,
            'cell_donor_over_continuum': math.fsum(cell_flux), 'cell_donor_over_label': math.fsum(cell_flux)*factor,
            'face_state_on_cell_footprint_over_continuum': math.fsum(face_flux),
            'face_state_on_face_footprint_over_continuum': math.fsum(pointed_flux),
            'lateral_face_state_on_cell_footprint_over_continuum': math.fsum(side_flux),
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', nargs='?', type=Path, default=Path(__file__).with_name('cap_reference_fixture.json'))
    rows = list(measure(json.loads(parser.parse_args().fixture.read_bytes())))
    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
