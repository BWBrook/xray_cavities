import csv,json,datetime
from pathlib import Path
import h5py,numpy as np
root=Path('/u/bwbrook/xray_cavities_analysis/2026-08-31-selected-age-native-shock-r1')
covered=[]
for case in ['C-HI','C-LO','G-HI','G-LO']:
    with (root/(case+'_source_manifest.csv')).open() as f:
        rows=list(csv.DictReader(f))
    for row in rows:
        path=Path(row['input_h5'])
        if case=='G-HI' and int(row['snapshot_index'])==10:
            path=Path('/u/bwbrook/xray_cavities_runs/2026-08-21-g-hi-full-history-home-continuation/G-HI/particles/problem/outputs/data.0010.flt.h5')
        with h5py.File(path,'r') as h5:
            tr=h5[row['timestep']+'/vars/tr1']
            dtype=tr.dtype
            shape=list(tr.shape)
            time=float(h5[row['timestep']].attrs['Time'])
        if dtype.kind!='f' or dtype.itemsize!=4: raise ValueError(str(path)+': not float32')
        covered.append({'case':case,'snapshot_index':int(row['snapshot_index']),'input_h5':str(path),'timestep':row['timestep'],'tracer_dtype':dtype.str,'tracer_shape':shape,'file_size_bytes':path.stat().st_size,'actual_time_code':time})
proof={'primary_threshold':0.001,'strict_equivalent':True,'comparison_dtype':'float64','proof_method':'float32_threshold_not_representable_after_float64_promotion','covered_case_ages':covered,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'quantized_float32_threshold':float(np.float32(.001)),'scope':'stored-value comparison only; source-quantized equality energy sensitivity pending combined native/shock pass'}
print(json.dumps(proof))
