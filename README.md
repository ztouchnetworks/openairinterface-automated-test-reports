# OAI Report Generation Tool

Processes results from OpenAirInterface (OAI) iPerf3 tests run via Colosseum batch jobs and generates HTML report of test results.
This is used to analyze automatic OAI tests run as part of the OAI Jenkins CI, for example via [this](https://jenkins-oai.eurecom.fr/job/RAN-Trigger-NEU-CI/) job.

Results of successful tests are saved in history files and used to compare new analyzed tests.
For instance, a test is considered successful if the achieved throughput is greather than or equal to the target transmit rate (if one is specified), or of the test history (if the target transmit rate is not specified).

The processing tool can also be called as standalone to analyze OAI results, as described below.
Please note that in this case, `n/a` might appear in some info fields of the generated test report.

## Call as Standalone Tool

Call as

```bash
python3 generate_oai_report.py --results_dir path/to/reservation/directory
```

If not specified, the parent directory of the `results_dir` is used to save/load the test history results.
This directory can also be explicitly passed as

```bash
python3 generate_oai_report.py --results_dir path/to/reservation/directory --history_dir path/to/test/history/directory
```

Other optional parameters, e.g., related to Ansible and Jenkins build times can be passed.

## Call via Docker Compose

The processing tool can also be called through the provided Docker Compose [file](docker-compose.yaml), which mounts as volumes both the test results and test history directories.
These directories are derived from the local shell environment through the `RESULTS_DIR` and `HISTORY_DIR` environment variables.
Extra arguments can be passed via the `EXTRA_ARGS` variables.

Bring up Docker Compose with

```bash
RESULTS_DIR=path/to/reservation/directory \
  HISTORY_DIR=path/to/test/history/directory \
  EXTRA_ARGS="--job_id_jenkins 143" \
  docker-compose up
```

Bring down Docker Compose with

```bash
docker-compose down
```

Examples of reservation and history directory can be found in the OAI Jenkins [test instances](https://jenkins-oai.eurecom.fr/job/RAN-Trigger-NEU-CI/).