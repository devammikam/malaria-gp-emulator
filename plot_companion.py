"""Create labelled figures from executed companion outputs, never invented results."""
from pathlib import Path
import argparse,json,shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot(name,folder):
    folder=Path(folder);output=folder/'companion_figure.png'
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    if name=='winnie':shutil.copy2(folder/'profile_demo.png',output);return output
    if name=='peter':
        d=pd.read_csv(folder/'synthetic_policy_grid.csv')
        fig,axs=plt.subplots(1,3,figsize=(10,3.4),sharey=True)
        for ax,(nu,b) in zip(axs,d.groupby('immigration')):
            for duration,g in b.groupby('duration'):
                g=g.sort_values('lag');y=g.risk_establishment_proxy
                errors=np.maximum(0,np.vstack([y-g.monte_carlo_wilson95_low,g.monte_carlo_wilson95_high-y]))
                ax.errorbar(g.lag,y,yerr=errors,marker='o',capsize=2,label=str(duration)+' generations')
            ax.set(title='Imports per generation '+str(nu),xlabel='Response lag in generations')
        axs[0].set_ylabel('Sustained-growth proxy probability');axs[-1].legend(title='Response duration',fontsize=8)
        fig.suptitle('Synthetic vector invasion example with Wilson simulation intervals')
    elif name=='antony':
        data=json.loads((folder/'synthetic_decision_design.json').read_text())
        fig,ax=plt.subplots(figsize=(8,3.8));n=len(next(iter(data['results'].values()))['allocation']);x=np.arange(n)
        for j,(label,record) in enumerate(data['results'].items()):
            ax.bar(x+(j-.5)*.34,[r['additional_samples'] for r in record['allocation']],.34,label=label.replace('_',' '))
        ax.set_xticks(x,[r['site'] for r in record['allocation']]);ax.set_ylabel('Additional tests')
        ax.set_title('Synthetic surveillance allocation under declared selection scenarios');ax.legend(fontsize=9)
    elif name=='lucy':
        data=json.loads((folder/'ledger.json').read_text());baseline=data['baseline']['total']
        rows=data['policies'];fig,axs=plt.subplots(1,2,figsize=(9,3.5));x=np.arange(len(rows))
        primary=[r['total']['primary_completers']-baseline['primary_completers'] for r in rows]
        nxt=[r['total']['next_dose']-baseline['next_dose'] for r in rows]
        axs[0].bar(x-.16,primary,.32,label='Primary completers');axs[0].bar(x+.16,nxt,.32,label='Next dose recipients')
        axs[0].set_xticks(x,[r['policy'] for r in rows]);axs[0].set_ylabel('Expected additional children');axs[0].legend(fontsize=8)
        axs[1].bar(x,[r['additional_hours'] for r in rows],color=['#366C91','#9A5A2E'])
        axs[1].set_xticks(x,[r['policy'] for r in rows]);axs[1].set_ylabel('Additional staff hours')
        fig.suptitle('Synthetic complete-cohort delivery ledger with matched additional capacity')
    elif name=='ammikam':
        d=pd.read_csv(folder/'heldout_predictions.csv')
        audit=pd.read_csv(folder/'decision_audit.csv')
        fig,axs=plt.subplots(1,2,figsize=(10,3.8))
        for eir,g in d.groupby('held_eir'):
            axs[0].scatter(g.native_replicate_mean,g.prediction,label='Held out EIR '+str(eir))
        axs[0].plot([0,1],[0,1],color='gray',linestyle=':')
        axs[0].set(xlabel='Two-seed native mean prevalence',ylabel='Held-out emulator prediction',xlim=(0,1),ylim=(0,1))
        axs[0].legend(fontsize=8)
        for eir,g in audit.groupby('held_eir'):
            axs[1].plot(g.effort_weight,g.conservative_native_regret_upper,label='EIR '+str(eir))
        axs[1].axhline(float(audit.delta.iloc[0]),color='black',linestyle=':',label='Declared regret tolerance')
        axs[1].set(xlabel='Illustrative effort weight',ylabel='Conservative native regret upper bound')
        axs[1].legend(fontsize=8)
        fig.suptitle('Uncalibrated Imperial example: two seeds require conservative abstention')
    elif name=='steve':
        d=pd.read_csv(folder/'forecast_demonstration.csv')
        fig,axs=plt.subplots(1,2,figsize=(10,3.8))
        first=d.origin.min();g=d.loc[d.origin.eq(first)]
        regions=sorted(g.region.unique());x=np.arange(len(regions))
        target=g.groupby('region').target_365_day_recorded_episodes.first().reindex(regions)
        axs[0].bar(x-.24,target,.24,label='Consolidated recorded target')
        models=sorted(g.model.unique())
        for j,model in enumerate(models):
            pred=g.loc[g.model.eq(model)].set_index('region').predicted_median.reindex(regions)
            axs[0].bar(x+j*.24,pred,.24,label=model.replace('_',' '))
        axs[0].set_xticks(x,['Region '+str(r) for r in regions])
        axs[0].set_ylabel('Recorded episodes');axs[0].set_title('First retained forecast origin '+str(first));axs[0].legend(fontsize=7)
        for model,h in d.groupby('model'):
            scores=h.groupby('origin').wis_plugin_demonstrator.mean()
            axs[1].plot(range(len(scores)),scores.values,marker='o',label=model.replace('_',' '))
        origins=sorted(d.origin.unique())
        axs[1].set_xticks(range(len(origins)),[str(v)[:7] for v in origins],rotation=35,ha='right',fontsize=8)
        axs[1].set_ylabel('Mean plug-in weighted interval score');axs[1].set_title('Illustrative limited-origin execution');axs[1].legend(fontsize=8)
        fig.suptitle('Historical Guyana reporting example; no climate gain estimated')
    elif name=='rachael':
        data=json.loads((folder/'decision.json').read_text());p=data['selected_minimax_regret'][0]
        fig,axs=plt.subplots(1,2,figsize=(10,3.8));states=list(p['costs']);years=np.arange(1,len(p['costs'][states[0]])+1)
        for state in states:axs[0].plot(years,p['costs'][state],marker='o',label=state.replace('_',' '))
        axs[0].set(xlabel='Illustrative programme year',ylabel='Annual cost in arbitrary units')
        axs[0].legend(fontsize=8)
        x=np.arange(len(states));axs[1].bar(x,[p['burden'][s] for s in states],label='Selected feasible portfolio')
        axs[1].plot(x,[data['state_specific_oracle_burden'][s] for s in states],'kx',label='State-specific oracle')
        axs[1].set_xticks(x,[s.replace('_','\n') for s in states],fontsize=8)
        axs[1].set_ylabel('Synthetic severe-burden units');axs[1].legend(fontsize=8)
        fig.suptitle('Synthetic finite-library accounting and regret check')
    else:
        # Other companions produce their own scientifically defined figure.
        candidates=[p for p in sorted(folder.glob('*.png')) if p.name!='companion_figure.png']
        if not candidates:raise FileNotFoundError('No defined companion figure for '+name)
        shutil.copy2(candidates[0],output);return output
    fig.tight_layout();fig.savefig(output,dpi=170,bbox_inches='tight');plt.close(fig);return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('folder');a=p.parse_args()
    print(plot(a.name,a.folder))
