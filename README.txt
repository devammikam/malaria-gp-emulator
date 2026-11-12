Ammikam Mwangi RESEARCH COMPANION

The uncalibrated native reference has nine configurations and two seeds per configuration. Complete EIR levels are held out for the emulator example. Conservative direct-simulator bounds leave every demonstrated decision unresolved, which is valid abstention at this sample size. Adequate native replication, adaptive design, calibrated policy scenarios and external validation remain research work.

SETUP
Use Python 3 with the pinned packages in requirements.txt.
  python -m pip install -r requirements.txt

EXECUTED LAUNCH COMMAND
  python ammikam_code.py --input native_reference/integration_summary.csv --out results
  python plot_companion.py ammikam results

The executed notebook Companion.ipynb and its HTML view contain saved outputs.
Install Jupyter separately if you wish to rerun the notebook; the Python command works without it.
Read EXECUTION_RECORD.json. The small demonstrations are not the completed study.
Use distinct folders for synthetic examples and empirical or calibrated research.

NATIVE IMPERIAL REFERENCE
The separately executed example uses malariasimulation 3.0.0.
Use your group's validated R library, or run Rscript install_R.R.
Then run: Rscript imperial_experiments.R emulator results/native
The archived combined-run example uses 1825 follow-up days. Standalone observation
and emulator modes use 730 days. Read the run summary, not the folder name, for the horizon.
All supplied native examples are uncalibrated and use only two stochastic replicates.
Country site-file access is not required by these examples.
