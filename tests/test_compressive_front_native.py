from pathlib import Path
import sys

import numpy as np
from scipy import ndimage

SCIENCE = Path(__file__).resolve().parents[1] / 'scripts/science'
sys.path.insert(0, str(SCIENCE))
from compressive_front_native import derivative, local_masks, select_components
from independent_bow_shock import Grid3D


def test_wide_and_narrow_derivatives_respect_actual_centres():
    x = np.array([-3.3,-2.1,-.85,-.1,.6,1.7,3.,4.5,6.1])
    field = np.broadcast_to((x**2)[None,None,:],(3,4,len(x)))
    for step in (1,2):
        got = derivative(field,2,x,step)
        assert np.allclose(got[:,:,step:-step],2*x[step:-step],rtol=1e-12,atol=1e-14)


def test_source_region_patches_are_ranked_separately_and_boundary_stays_excluded():
    edge = np.arange(-20.,21.)
    c = (edge[:-1]+edge[1:])/2
    grid = Grid3D(c,c,c,edge,edge,edge)
    cells = np.zeros(grid.shape,dtype=bool)
    cells[6:13,8:12,9:15] = True
    cells[24:30,12:18,13:21] = True
    cells[25:28,24:28,24:28] = True
    cells[3:37,3:9,2:4] = True
    cells[17:19,25:27,28:30] = True
    labels,count=ndimage.label(cells,structure=np.ones((3,3,3)))
    selection=select_components(labels,count,grid,np.ones(grid.shape))
    assert selection.winners==(labels[8,10,11],labels[25,14,16])
    assert selection.boundary[labels[20,5,2]]
    assert selection.eligible[labels[26,25,25]]
    assert not selection.eligible[labels[17,25,28]]
    main,other,edge=local_masks(labels[26],selection,True)
    assert main[14,16] and other[25,25] and edge[5,2]
    assert not np.any((main&other)|(main&edge)|(other&edge))
