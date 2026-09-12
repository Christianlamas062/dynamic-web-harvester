# Dynamic Web Harvester 🚀

[![CI Pipeline](https://github.com/Christianlamas062/dynamic-web-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/Christianlamas062/dynamic-web-harvester/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium%20Headless-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.x-E92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![AWS S3 Data Lake](https://img.shields.io/badge/AWS%20S3-Data%20Lake%20Sink-FF9900.svg?logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Boto3](https://img.shields.io/badge/Boto3-AWS%20SDK-232F3E.svg?logo=amazonwebservices&logoColor=white)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
[![Pandas](https://img.shields.io/badge/Pandas-2.2+-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Pytest](https://img.shields.io/badge/Tested%20with-Pytest-0A9EDC.svg?logo=pytest&logoColor=white)](https://pytest.org/)
[![Code Style: Strict Typing](https://img.shields.io/badge/Typing-Strict%20Type%20Hints-informational.svg)](https://peps.python.org/pep-0484/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A dynamic, asynchronous web data extraction and processing pipeline engineered for production environments. Built with Python featuring browser automation via **Playwright**, data contract validation with **Pydantic v2**, automated date-partitioned raw payload ingestion into **Amazon S3 (Data Lakehouse)** via **Boto3**, and a lightweight ETL engine powered by **Pandas** for deduplication, sorting, and multi-format export (CSV / Excel). Fully containerized with **Docker** and **Docker Compose** for zero-configuration client delivery.

---

## 🗄️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Dynamic Scraper (Playwright Async)"]
        A[Target: books.toscrape.com] -->|Chromium Headless| B(DOM Traversal & Product Pods)
        B -->|Pagination Loop| C{Next Page Link?}
        C -- Yes & page < max_pages --> B
        C -- No or Limit Reached --> D[Raw Elements Stream]
    end

    subgraph Validation ["2. Schema Enforcement (Pydantic v2)"]
        D --> E[ScrapedProduct Schema]
        E -->|Clean Whitespace| F[Title Validator]
        E -->|Regex Clean & >= 0.0| G[Price Validator]
        E -->|Textual to Float 0-5| H[Rating Validator]
        E -->|Textual to Bool| I[Availability Validator]
    end

    subgraph Persistence ["3. Dual Persistence Layer"]
        F & G & H & I -->|Validated DTOs| S3Sink["Amazon S3 Lakehouse Sink (Boto3)"]
        S3Sink --> S3Store[("s3://bucket/raw/YYYY/MM/DD/HHMMSS_records.json")]

        F & G & H & I -->|Ingestion| ETL["Data Pipeline & ETL (Pandas)"]
        ETL --> Dedupe[Deduplication by Title]
        Dedupe --> Sort[Sorting by Criteria]
        Sort --> LocalStore{"Local Storage Switcher"}
        LocalStore -- CSV --> CSVFile[("data/processed/*.csv")]
        LocalStore -- Excel --> XLSXFile[("data/processed/*.xlsx")]
    end
```

---

## ☁️ Cloud Architecture & Amazon S3 Lakehouse Sink

Unlike basic scrapers that write volatile local text files, this pipeline implements an **Enterprise Data Lakehouse Architecture** for raw payload persistence:

```text
Playwright Crawler ──> Pydantic Schema Validation ──┬──> Amazon S3 Lakehouse Sink (Raw JSON)
                                                    └──> Local ETL Pipeline (CSV / Excel)
```

### Key Cloud Capabilities
- **Automated Date Partitioning:** Payloads are automatically partitioned using standard data lake hierarchy: `raw/YYYY/MM/DD/HHMMSS_records.json`, optimizing downstream querying with AWS Athena, Glue, or Spark.
- **Fail-Safe Client Architecture:** Managed through `botocore.exceptions.ClientError` with comprehensive structured logging.
- **Stateless Cloud Portability:** S3 credentials and bucket target configurations are completely decoupled via standard 12-Factor App environment variables.
- **Automated Lifecycle Policy & FinOps Cost Optimization:** Ingestion bucket includes an automated lifecycle configuration:
  - **Transition:** Objects with prefix `raw/` automatically transition to `GLACIER` (Glacier Flexible Retrieval) after **30 days**.
  - **Expiration:** Historical payloads automatically expire and delete after **90 days** for cost-free data lifecycle management.
  - Executable standalone via `python scripts/setup_s3_lifecycle.py` or programmatically via `S3DataSink.configure_lifecycle_policy()`.

### Required Environment Variables

Configure the following variables in a `.env` file at project root (see `.env.example`):

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | IAM User Access Key with S3 PutObject permission | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | IAM User Secret Access Key | `OA6c...` |
| `AWS_DEFAULT_REGION` | AWS Region where the target S3 bucket resides | `us-east-1` |
| `S3_BUCKET_NAME` | Destination S3 Bucket for the Data Lake | `harvester-data-christian-2026` |

### One-Step Unified Deployment

Deploy and execute the complete pipeline (including automated S3 upload) with a single command:

```bash
# Copy template and fill your credentials (once)
cp .env.example .env

# Single-command build & run
docker compose up --build
```

---

## 🌟 Engineering Highlights

- **CI/CD Quality Gate with GitHub Actions:** Automated continuous integration pipeline running full test suites and Playwright headless drivers on every push and PR to `main`.
- **Asynchronous Crawler with Playwright:** Headless Chromium automation with realistic User-Agent headers, standard viewports, and explicit 10-second operation timeouts.
- **Intelligent Pagination:** Automatically discovers and traverses pagination links (`li.next a`) until all catalog pages are exhausted or the `--max-pages` threshold is reached.
- **Strict Data Contracts with Pydantic v2:**
  - Automatic whitespace trimming across all textual fields and URLs.
  - Robust currency parsing (e.g., `"£51.77"` ➔ `51.77`) with numeric validation enforcing `price >= 0.0`.
  - Semantic star rating conversion (`"One"` through `"Five"` ➔ `1.0` through `5.0`).
  - Parsing inventory availability strings into native boolean flags.
- **Automated Cloud Lakehouse Persistence:** Asynchronous upload of validated JSON payloads to AWS S3 with timestamped directory partitioning (`raw/YYYY/MM/DD/...`).
- **Deduplication & Cleaning via Pandas:** Removes duplicate items by title while preserving the initial occurrence and provides configurable column-based sorting.
- **Containerized & Production Ready:** Includes pre-configured `Dockerfile` with official Playwright runtime and `docker-compose.yml` with `.env` secret injection and host volume mapping.
- **Graceful Fault Tolerance:** Element-level exception boundaries ensure missing attributes or corrupted DOM nodes are logged without aborting batch execution.
- **Structured Standard Logging:** Replaces all arbitrary `print()` statements with Python's standard `logging` module, including timestamps, log levels (`INFO`, `DEBUG`, `WARNING`, `ERROR`), and structured messages.
- **Strict Type Hinting:** Full PEP 484 type annotations on all function and method signatures for superior maintainability and static analysis support.

---

## 📁 Project Structure

```text
dynamic-web-harvester/
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions automated CI testing pipeline
├── .env.example              # Environment variable template for cloud deployment
├── data/
│   └── processed/            # Export destination for CSV and Excel files (git-ignored)
├── scripts/
│   └── setup_s3_lifecycle.py # Automated S3 lifecycle and glacier transition configuration
├── src/
│   ├── __init__.py           # Package initializer
│   ├── models.py             # Pydantic v2 schemas and validators
│   ├── pipeline.py           # Cleaning, deduplication, and export pipeline
│   ├── scraper.py            # Asynchronous scraper using Playwright Chromium
│   └── storage.py            # Amazon S3 Lakehouse Sink (Boto3 integration)
├── tests/
│   ├── __init__.py
│   ├── test_models.py        # Unit tests for schemas and data integrity
│   ├── test_pipeline.py      # Unit tests for transformations and file exports
│   └── test_scraper.py       # Unit tests for scraper logic without network calls
├── .dockerignore             # Context filter for efficient image builds
├── .gitignore                # Exclusion rules for data, logs, and caches
├── docker-compose.yml        # Zero-config execution and volume orchestration
├── Dockerfile                # Multi-stage/headless Playwright container image
├── main.py                   # CLI entrypoint with argparse and pipeline orchestration
├── README.md                 # Technical project documentation
└── requirements.txt          # Production and testing dependencies
```

---

## 🐳 Docker Deployment & Quickstart (Recommended)

The harvester is fully containerized using Microsoft's official Playwright image (`python:v1.49.0-jammy`) with all Chromium OS dependencies pre-installed.

### Option A: Via Docker Compose (Zero-Configuration Client Execution)

Run the full pipeline with a single command without rebuilding or managing dependencies:

```bash
docker compose up --build
```

* Processed datasets (`.csv` or `.xlsx`) are automatically written to your local `data/processed/` folder via volume mapping.
* Parameters (e.g. `--max-pages 10`) can be modified directly under the `command` key in `docker-compose.yml`.

### Option B: Via Docker CLI

```bash
# 1. Build the image
docker build -t dynamic-web-harvester .

# 2. Run extraction with customized arguments
docker run --rm -v $(pwd)/data/processed:/app/data/processed dynamic-web-harvester --max-pages 3 --format excel
```

> [!TIP]
> **Linux / macOS Volume Permissions:**  
> In Linux and macOS environments, files written to mounted volumes by default can be owned by `root`. To ensure output files match your local user permissions without needing `sudo` to modify or delete them, pass the `--user` flag:
> ```bash
> docker run --rm --user $(id -u):$(id -g) -v $(pwd)/data/processed:/app/data/processed dynamic-web-harvester
> ```

### Run Automated Tests Inside Docker

Verify pipeline integrity and schema validation in an isolated container environment:

```bash
docker run --rm --entrypoint pytest dynamic-web-harvester tests/ -v
```

---

## 🚀 Local Installation (Without Docker)

### 1. Clone the Repository and Navigate to Root

```bash
git clone https://github.com/Christianlamas062/dynamic-web-harvester.git
cd dynamic-web-harvester
```

### 2. Configure Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies and Browser Binaries

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 💻 CLI Usage Guide

The harvester provides an intuitive command-line interface powered by `argparse`:

```text
usage: dynamic-web-harvester [-h] [--max-pages MAX_PAGES] [--format {csv,excel}]
                             [--output-dir OUTPUT_DIR] [--log-level {DEBUG,INFO,WARNING,ERROR}]

Production-grade asynchronous web scraping pipeline using Playwright and Pandas.

options:
  -h, --help            show this help message and exit
  --max-pages MAX_PAGES
                        Maximum number of pages to scrape (default: 2)
  --format {csv,excel}  Target export format: 'csv' or 'excel' (default: 'csv')
  --output-dir OUTPUT_DIR
                        Destination directory for processed output files (default: 'data/processed')
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        Logging verbosity level (default: 'INFO')
```

### Execution Examples

#### 1. Rapid Single-Page Extraction (CSV):
```bash
python main.py --max-pages 1 --format csv
```

#### 2. Multi-Page Extraction (5 Pages to Excel):
```bash
python main.py --max-pages 5 --format excel
```

#### 3. Diagnostic Mode with Verbose Logging:
```bash
python main.py --max-pages 2 --format csv --log-level DEBUG
```

---

## 🧪 Automated Testing

The project includes an exhaustive unit testing suite implemented with `pytest` and `pytest-asyncio`. Tests execute **100% offline** using isolated fixtures and Playwright mock objects:

```bash
pytest -v
```

### Test Coverage Overview:
- **`tests/test_models.py`**:
  - Schema instantiation and automatic whitespace stripping.
  - Currency extraction and string-to-float conversions.
  - Price non-negativity constraint validation (`price >= 0.0`).
  - Validation error handling for non-numeric and corrupted price values.
  - Mandatory non-empty title enforcement.
  - Textual star rating mapping (`"One"` through `"Five"`) and boundary checks (`0.0` to `5.0`).
  - String inventory availability parsing to booleans.
- **`tests/test_pipeline.py`**:
  - Duplicate record suppression by product title.
  - Ascending and descending price ordering.
  - Safe handling of empty datasets.
  - Multi-format file export verification (CSV and Excel) via `tmp_path`.
  - Rejection of unsupported export format strings.
- **`tests/test_scraper.py`**:
  - Asynchronous product card parsing using mocked Playwright locators.
  - Resilient behavior and non-crashing fallback handling when encountering missing DOM elements.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
