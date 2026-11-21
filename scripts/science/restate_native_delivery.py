"""Match current native enthalpy to cumulative signed injector gas delivery."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
CASES={'C-HI':50,'C-LO':50,'G-HI':47,'G-LO':50}
METHODS=('linear_snapshot_flags','first_order_snapshot_flags','linear_hllc','linear_hll')
RULES={'left':0.,'trapezoid':.5,'right':1.}
PRIMARY=('linear_snapshot_flags','trapezoid')
SECONDS=365.25*86400*1e6
INJECTOR=ROOT/'docs/science/assets/production_injector_histories_2026-11-21'
NATIVE=ROOT/'docs/science/assets/turn15_review_2026-11-11/budgets'
HISTORICAL=ROOT/'docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis'


def digest(raw):return hashlib.sha256(raw).hexdigest()


def csv_rows(raw):return list(csv.DictReader(io.StringIO(raw.decode())))


def write(path,rows):
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def run(output,figure=True):
    checks=[];hashes={}
    def read(path):
        raw=path.read_bytes();hashes[str(path.relative_to(ROOT))]=digest(raw);return raw
    def equal(a,b,label):
        residual=abs(a-b)/max(abs(a),abs(b),1.)
        if residual>2e-11:raise ValueError(f'{label}: inconsistent numbers {a}, {b}')
        checks.append(residual)
    receipt=json.loads(read(INJECTOR/'verification.json'))
    archive=read(INJECTOR/'history_tables.zip')
    if digest(archive)!=receipt['public_zip_sha256']:raise ValueError('injector archive hash differs')
    tables={}
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for name,expected in receipt['public_member_sha256'].items():
            raw=bundle.read(name)
            if digest(raw)!=expected:raise ValueError(f'injector member hash differs: {name}')
            tables[name]=csv_rows(raw)
    labels={}
    for row in tables['comparison/flagged_sphere_gravity_intervals.csv']:
        key=row['case'],int(row['end_index'])
        value=float(row['labelled_energy_erg'])
        if key in labels:equal(value,labels[key],f'{key}/shared label')
        labels[key]=value
    results=[]
    for case,last in CASES.items():
        power=2e45 if case.endswith('HI') else 2e43
        snapshot_rows=tables[f'native/summary/{case}/injector_snapshot_rates.csv']
        snapshot={(int(r['index']),r['method'],r['region']):r for r in snapshot_rows}
        if not len(snapshot)==len(snapshot_rows)==12*(last+1):raise ValueError('invalid snapshot inventory')
        if set(snapshot)!={(i,m,r) for i in range(last+1) for m in METHODS for r in ('cap','stationary','net')}:
            raise ValueError(f'{case}: incomplete or duplicate snapshot rate selection')
        interval_rows=tables[f'native/summary/{case}/injector_interval_balances.csv']
        interval={(int(r['start_index']),int(r['end_index']),r['method'],r['rule']):r for r in interval_rows}
        if len(interval)!=len(interval_rows) or set(interval)!={(i-1,i,m,r) for i in range(1,last+1) for m in METHODS for r in RULES}:
            raise ValueError(f'{case}: incomplete or duplicate interval selection')
        age={i:float(snapshot[i,PRIMARY[0],'net']['age_myr']) for i in range(last+1)}
        if age[0]!=0 or any(age[i]<=age[i-1] for i in range(1,last+1)):raise ValueError('invalid actual ages')
        for row in snapshot_rows:
            if row['case']!=case:raise ValueError('case mismatch')
            equal(float(row['age_myr']),age[int(row['index'])],f'{case}/rate actual age')
        native_rows=csv_rows(read(NATIVE/case/'measurements.csv'))
        native={int(r['snapshot_index']):r for r in native_rows if r['speed_threshold_km_s']=='100'}
        old_rows=csv_rows(read(HISTORICAL/case/'native_energy_selected_age.csv'))
        old={int(r['snapshot_index']):r for r in old_rows if r['side']=='bipolar_total' and r['partition_method']=='binary_threshold_1e-3'}
        selected=[10,20,30,40]+([50] if last==50 else [])
        if set(old)!=set(selected):raise ValueError('historical selected-age surface differs')
        for i in selected:
            n=native[i];h=float(n['native_enthalpy_2.5_erg']);historic=float(old[i]['lobe_enthalpy_2p5pv_erg'])
            equal(float(n['actual_time_myr']),age[i],f'{case}/{i}/native actual age')
            equal(float(old[i]['actual_time_myr']),age[i],f'{case}/{i}/historical actual age')
            label=power*min(age[i],50.)*SECONDS
            equal(float(n['injected_energy_erg']),label,f'{case}/{i}/native label')
            equal(float(n['native_enthalpy_4_erg']),1.6*h,f'{case}/{i}/enthalpy convention')
            for method in METHODS:
                for rule,w in RULES.items():
                    terms=[];interval_terms=[];cone=[];stationary=[]
                    for end in range(1,i+1):
                        dt=(age[end]-age[end-1])*SECONDS
                        active_dt=(min(age[end],50.)-min(age[end-1],50.))*SECONDS
                        elabel=power*active_dt
                        equal(labels[case,end],elabel,f'{case}/{end}/active label')
                        def weighted(region):
                            return ((1-w)*float(snapshot[end-1,method,region]['gas_energy_over_label'])
                                    +w*float(snapshot[end,method,region]['gas_energy_over_label']))*power*dt
                        c,s,net=weighted('cap'),weighted('stationary'),weighted('net')
                        equal(c+s,net,f'{case}/{end}/{method}/{rule}/signed regions')
                        terms.append(net);cone.append(c);stationary.append(s)
                        interval_terms.append(float(interval[end-1,end,method,rule]['net_gas'])*elabel)
                    gas=math.fsum(terms)
                    equal(gas,math.fsum(interval_terms),f'{case}/{i}/{method}/{rule}/cumulative independent routes')
                    equal(math.fsum(labels[case,end] for end in range(1,i+1)),label,f'{case}/{i}/cumulative label')
                    if gas<=0:raise ValueError('nonpositive cumulative net gas denominator')
                    stored=float(n['all_total_delta_erg'])
                    results.append(dict(case=case,snapshot_index=i,actual_age_myr=age[i],method=method,quadrature=rule,
                        native_enthalpy_2p5pv_erg=h,historical_Q029_enthalpy_2p5pv_erg=historic,
                        historical_minus_primary_fraction=(historic-h)/h,cumulative_net_gas_delivery_erg=gas,
                        cumulative_cone_gas_erg=math.fsum(cone),cumulative_stationary_gas_erg=math.fsum(stationary),
                        labelled_cumulative_kinetic_energy_erg=label,net_gas_delivery_over_label=gas/label,
                        native_2p5pv_over_cumulative_net_gas=h/gas,native_2p5pv_over_label=h/label,
                        native_4pv_over_cumulative_net_gas=1.6*h/gas,R100_stored_change_erg=stored,
                        R100_stored_change_over_cumulative_net_gas=stored/gas,native_2p5pv_over_R100_stored_change=h/stored,
                        R100_domain_geometry_status=n['domain_geometry_status'],R100_measurement_hold_codes=n['measurement_hold_codes']))
    output.mkdir(parents=True,exist_ok=True)
    primary=[r for r in results if (r['method'],r['quadrature'])==PRIMARY]
    ranges=[]
    for case in CASES:
        rows=[r for r in primary if r['case']==case]
        ranges.append(dict(case=case,selected_age_count=len(rows),first_age_myr=min(r['actual_age_myr'] for r in rows),last_age_myr=max(r['actual_age_myr'] for r in rows),
            enthalpy_over_net_gas_min=min(r['native_2p5pv_over_cumulative_net_gas'] for r in rows),
            enthalpy_over_net_gas_max=max(r['native_2p5pv_over_cumulative_net_gas'] for r in rows),
            enthalpy_over_label_min=min(r['native_2p5pv_over_label'] for r in rows),
            enthalpy_over_label_max=max(r['native_2p5pv_over_label'] for r in rows),
            cumulative_net_gas_over_label_min=min(r['net_gas_delivery_over_label'] for r in rows),
            cumulative_net_gas_over_label_max=max(r['net_gas_delivery_over_label'] for r in rows)))
    matched=[r for r in primary if r['snapshot_index']==30]
    write(output/'selected_age_scenarios.csv',results)
    write(output/'primary_selected_ages.csv',primary)
    write(output/'claim_ranges.csv',ranges)
    write(output/'matched_30myr.csv',matched)
    if figure:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        data=csv_rows((output/'matched_30myr.csv').read_bytes())
        fig,ax=plt.subplots(figsize=(7.2,2.6),layout='constrained')
        for y,row in enumerate(reversed(data)):
            supply=float(row['native_2p5pv_over_cumulative_net_gas']);reference=float(row['native_2p5pv_over_label'])
            ax.barh(y+.13,reference,height=.22,color='#b4bbc0',label='Labelled kinetic energy' if y==0 else None)
            ax.barh(y-.13,supply,height=.22,color='#24647a',label='Reconstructed gas supply' if y==0 else None)
            ax.text(supply+.012,y-.13,f'{100*supply:.0f}%',va='center',fontsize=10,color='#163f4e')
        ax.set(yticks=range(4),yticklabels=[r['case'] for r in reversed(data)],xlim=(0,1.12),
               xlabel='Native 2.5pV / cumulative energy at 30 Myr')
        ax.set_xticks([0,.25,.5,.75,1],labels=['0%','25%','50%','75%','100%'])
        ax.legend(frameon=False,loc='lower left',bbox_to_anchor=(0,1.02),ncol=2,fontsize=9)
        ax.spines[['top','right']].set_visible(False)
        for extension in ('png','pdf','svg'):fig.savefig(output/f'native_delivery_30myr.{extension}',dpi=180)
        plt.close(fig)
    report=dict(status='reproduced_matched_native_delivery_ratios',primary_method=PRIMARY[0],primary_quadrature=PRIMARY[1],
        primary_selected_rows=len(primary),sensitivity_rows=len(results),numeric_checks=len(checks),maximum_relative_check_residual=max(checks),
        maximum_relative_historical_numerator_difference=max(abs(r['historical_minus_primary_fraction']) for r in primary),
        numerator='current whole binary-lobe 2.5*sum(pV), tr1>1e-3, exact native finite-volume geometry',
        denominator='signed cone plus stationary gas-energy flux, saved-state reconstruction, cumulative from initialized t0 to the identical case/age',
        input_sha256=hashes,archive_member_sha256=receipt['public_member_sha256'],script_sha256=digest(Path(__file__).read_bytes()),
        products_sha256={name:digest((output/name).read_bytes()) for name in
            ('selected_age_scenarios.csv','primary_selected_ages.csv','claim_ranges.csv','matched_30myr.csv')},
        limits=['saved-state quadrature omits intermediate RK stages and the unsaved terminal dip',
                'current absolute pV and signed moving-aperture storage are distinct estimands',
                'R100 total includes centre-zero fixed-potential energy and retains geometry/boundary holds',
                'no population calibration, scalar delivery correction or physical-closure promotion'])
    if figure:
        report['figure_sha256']={f'native_delivery_30myr.{ext}':digest((output/f'native_delivery_30myr.{ext}').read_bytes())
                                for ext in ('png','pdf','svg')}
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','primary_selected_rows','sensitivity_rows','numeric_checks','maximum_relative_check_residual')},indent=2))
    for row in ranges:print(row)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'docs/science/assets/native_delivery_restatement_2026-11-21')
    parser.add_argument('--no-figure',action='store_true')
    args=parser.parse_args();run(args.output_dir,not args.no_figure)
