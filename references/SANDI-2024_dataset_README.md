# DATASET

This dataset is part of the research work titled "A Dataset to Train Intrusion Detection Systems based on Machine Learning Models for Electrical Substations," which is currently awaiting approval for publication. The dataset has been meticulously curated to support the development and evaluation of machine learning models tailored for detecting cyber intrusions in the context of electrical substations. It is intended to facilitate research and advancements in cybersecurity for critical infrastructure, specifically focusing on real-world scenarios within electrical substation environments. We encourage its use for experimentation and benchmarking in related areas of study.

The code name of the dataset is **SANDI-2024** (Substation Anomaly Network Data for Intrusion detection 2024)

The following sections list the content of the dataset generated.

# Data

- **raw**
    - **iec6180**
        - *attack-free-data*
            - capture61850-attackfree.pcap (from real substation)
            - capture61850-attackfree_PTP.pcap
            - capture61850-attackfree_normalfault.pcap
        - *attack-data*
            - capture61850-floodattack_withfault.pcap
            - capture61850-floodattack_withoutfault.pcap
            - capture61850-fuzzyattack_withfault.pcap
            - capture61850-fuzzyattack_withoutfault.pcap
            - capture61850-replay.pcap
            - capture61850-ptpattack.pcap
     - **iec104**
        - *attack-free-data*
            - capture104-attackfree.pcap (from real substation)
        - *attack-data*
            - capture104-dosattack.pcap
            - capture104-floodattack.pcap
            - capture104-fuzzyattack.pcap
            - capture104-iec104starvationattack.pcap
            - capture104-mitmattack.pcap
            - capture104-ntpddosattack.pcap
            - capture104-portscanattack.pcap
- **processed**
    - **iec6180**
        - *attack-free-data*
            - capture61850-attackfree.csv
            - capture61850-attackfree_PTP.csv
            - capture61850-attackfree_normalfault.csv
        - *attack-data*
            - capture61850-floodattack_withfault.csv
            - capture61850-floodattack_withoutfault.csv
            - capture61850-fuzzyattack_withfault.csv
            - capture61850-fuzzyattack_withoutfault.csv
            - capture61850-replay.csv
            - capture61850-ptpattack.csv
        - *headers_iec61850[all].txt*
     - **iec104**
        - *attack-free-data*
            - capture104-attackfree.csv
        - *attack-data*
            - capture104-dosattack.csv
            - capture104-floodattack.csv
            - capture104-fuzzyattack.csv
            - capture104-iec104starvationattack.csv
            - capture104-mitmattack.csv
            - capture104-ntpddosattack.csv
            - capture104-portscanattack.csv
        - *headers_iec104[all].txt*

## Description

- **file type**: it may be *captured61850* or *captured104* depending on whether it contains network captures of the protocol IEC61850 or IEC104.
- **attack**: attack free (*attackfree*) or attack name is added to the file name.
- **function**: optionally, if there are some details about functionality captured (*normalfault*) or specific protocol capture (*PTP*).
- **file extension**: the type can be *PCAP* (network capture) or *CSV* (flow file).

# Results

- **results**
     - **test1-iec104**
        - model-test1-iec104.pkl
        - test1-iec104.log
     - **test1-iec61850**
        - model-test1-iec61850.pkl
        - test1-iec61850.log
     - **test2-iec61850**
        - model-test2-iec61850.pkl
        - test2-iec61850.log


## Description

The outcomes of different test executions are available as follows:

- **test1-iec104**: IEC 104 protocol for all attacks and attack free scenario
- **test1-iec61850**: IEC 61850 protocol for fuzzy attack with fault injection and attack free scenario
- **test2-iec61850**: IEC 61850 protocol for fuzzy attack normal operation and attack free scenario

Each test consists of the model results in Python pickle format (with a *.pkl* extension) and a detailed description of the execution conditions in an output log file (with a *.log* extension).


# Source Code

Tools to process network captures from IEC61850 and IEC104 can be found at [github repository](https://github.com/esguti/cybersecurity-datasets)
