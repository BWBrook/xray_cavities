"""Render the reviewed C-LO stored-energy history and flux scenario envelopes."""
from pathlib import Path
import argparse
import csv
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def render(inputs, output):
    history_path=inputs/'fixed_history.csv'
    scenarios_path=inputs/'cumulative_flux_scenarios.csv'
    history=[r for r in read(history_path) if r['fixed_box_total_over_label']]
    scenarios=read(scenarios_path)
    fig,axes=plt.subplots(2,1,figsize=(8.2,7.6),sharex=True,layout='constrained')
    times=[float(r['actual_time_myr']) for r in history]
    for key,label,color,style in (
        ('fixed_box_total_over_label','Fixed inset box','#0072B2','-'),
        ('R100_total_over_label','R100 sphere','#D55E00','--'),
        ('R300_total_over_label','R300 sphere','#009E73',':'),
    ):
        axes[0].plot(times,[float(r[key]) for r in history],label=label,color=color,
                     linestyle=style,linewidth=2)
    axes[0].axhline(1,color='0.3',linestyle=':',linewidth=1)
    axes[0].set(ylabel='Stored change / labelled input',
                title='A  Enlarging the aperture retains the early shortfall')
    axes[0].legend(frameon=False,loc='upper left',ncol=3,fontsize=9)
    for method,label,color in (
        ('outer_active_cell','Outer active cell','#0072B2'),
        ('linear_to_boundary_face','Linear to boundary face','#D55E00'),
    ):
        selected=[r for r in scenarios if r['domain_reconstruction']==method]
        ages=sorted({float(r['actual_age_myr']) for r in selected})
        lower=[]; upper=[]
        for age in ages:
            same=[r for r in selected if float(r['actual_age_myr'])==age]
            assert len(same)==3
            lower.append(min(float(r['outside_nozzle_inferred_source_over_label_min']) for r in same))
            upper.append(max(float(r['outside_nozzle_inferred_source_over_label_max']) for r in same))
        assert np.all(np.asarray(lower)<=np.asarray(upper))
        axes[1].fill_between(ages,lower,upper,color=color,alpha=.20,label=label)
        axes[1].plot(ages,lower,color=color,linewidth=1)
        axes[1].plot(ages,upper,color=color,linewidth=1)
    axes[1].axhline(0,color='0.3',linestyle=':',linewidth=1)
    axes[1].set(xlabel='Actual age (Myr)',ylabel='Outside-nozzle balance / labelled input',
                title='B  Outer-face reconstruction changes the source inference')
    axes[1].legend(frameon=False,loc='lower left',fontsize=9)
    for ax in axes:
        ax.grid(axis='y',color='0.9',linewidth=.6)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('C-LO: stored energy is measured; its numerical source remains unresolved',fontsize=12)
    fig.supxlabel('Centre-zero potential. Shaded ranges are scenarios, not confidence or error bounds.',fontsize=9)
    output.mkdir(parents=True,exist_ok=True)
    for extension in ('png','pdf'):
        fig.savefig(output/f'clo_history_review.{extension}',dpi=180)
    plt.close(fig)
    receipt={'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (history_path,scenarios_path)},
             'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'history_points':len(history),'scenario_rows':len(scenarios),
             'interpretation':'C-LO only; signed stored change and reconstructed source scenarios, not delivered energy or source localisation'}
    (output/'render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    render(args.inputs,args.output)
