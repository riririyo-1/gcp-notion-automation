## 概要

### 要件

1. スマホで記事閲覧
2. 共有ボタンから notion の DB に追加
3. python で notion api を叩き、要約や日付、メタデータを付与
4. 3 番を GCP の cloudrun や schedule 実行で自動化

### 開発範囲

1. docker 叩けば実行できる状態を実現済み
   - [github リポジトリ](https://github.com/riririyo-1/docker-notion-automation)
2. gcp で自動実行を実現済み
   現在、GUI から手動でデプロイ中。
3. 今回、terraform 化したい。

---

## 開発環境

### コーディング環境

- **OS:** Ubuntu 22.04
- **Editor:** VS Code
- **Language:** Python 3.12

### LLM 活用・開発フロー

自然言語中心の開発スタイルを採用。

- **Coding:** Claude Code / GitHub Copilot
- **Infra:** Terraform (GCP 状態を CLI で確認しながら宣言的に記述)

### モダン開発プラクティス

運用の手間を極小化し、本質的なロジック（プロンプト調整など）に集中するための構成。

- **CI/CD (GitHub Actions):**
  - `main` ブランチへの Push をトリガーに、Docker ビルド → Artifact Registry への Push → Cloud Run へのデプロイを完全自動化。
  - Terraform の `plan` / `apply` もワークフローに統合（予定）。
  - **OIDC (OpenID Connect):** サービスアカウントキー（JSON）を発行・保存せず、セキュアに GCP 認証を行う。

---

## Tech Stack

- **App:** Python, Docker, Notion API, OpenAI API
- **IaC:** Terraform
- **GCP:**
  - **Compute:** Cloud Run Jobs (バッチ処理として実行)
  - **Trigger:** Cloud Scheduler (Cron 起動)
  - **Security:** Secret Manager (API Key 管理) / IAM (Workload Identity)
  - **Registry:** Artifact Registry
- **CI/CD:** GitHub Actions

---

## folder structure

```text
gcp-notion-automation/
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD定義 (Build & Deploy)
├── .claude/
├── src/
│   ├── main.py              # アプリケーションのエントリーポイント
│   ├── requirements.txt
│   └── Dockerfile
├── terraform/               # Terraformコード
│   ├── main.tf              # リソース定義 (Cloud Run Jobs, Scheduler等)
│   ├── variables.tf
│   ├── provider.tf
│   └── backend.tf           # State管理 (GCS)
└── README.md
```

---

## Setup & Usage

### Prerequisites

- GCP プロジェクトの作成
- Terraform CLI のインストール
- gcloud CLI のインストール

```bash
# 0. Homebrewのインストール
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# 1. Install Terraform
brew install hashicorp/tap/terraform
# 2. Install Google Cloud SDK
# Linux の場合
sudo snap install google-cloud-cli --classic
# macOS の場合
brew install --cask google-cloud-sdk
# 3. GitHub CLI（CI/CDの状態確認やSecret設定に便利）
brew install gh
```

### GCP Initial Setup

```bash
# GCPログイン
gcloud auth login
gcloud auth application-default login
# プロジェクトIDを設定
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID
# 必要なAPIを有効化
gcloud services enable cloudrun.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### Terraform Setup

```bash
cd terraform
# 初期化
terraform init
# 変数ファイルを作成（terraform/terraform.tfvarsを編集）
cat <<EOF > terraform.tfvars
project_id = "your-gcp-project-id"
region = "asia-northeast1"
notion_api_key = "your-notion-api-key"
notion_database_id = "your-notion-database-id"
openai_api_key = "your-openai-api-key"
EOF
# プラン確認
terraform plan
# デプロイ
terraform apply
```

### Local Development

```bash
cd src
# 依存関係をインストール
pip install -r requirements.txt
# 環境変数を設定
export NOTION_API_KEY="your-notion-api-key"
export NOTION_DATABASE_ID="your-notion-database-id"
export OPENAI_API_KEY="your-openai-api-key"
# ローカル実行
python main.py
# Dockerでテスト
docker build -t notion-automation .
docker run -e NOTION_API_KEY="..." -e NOTION_DATABASE_ID="..." -e OPENAI_API_KEY="..." notion-automation
```

---

## CI/CD

GitHub Actions で自動デプロイを実現。

### GitHub Secrets の設定

以下の Secret を GitHub リポジトリに設定：

- `GCP_PROJECT_ID`: GCP プロジェクト ID
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: Workload Identity Provider の ID
- `GCP_SERVICE_ACCOUNT`: サービスアカウントのメールアドレス
- `NOTION_API_KEY`: Notion API キー
- `NOTION_DATABASE_ID`: Notion Database の ID
- `OPENAI_API_KEY`: OpenAI API キー

### デプロイフロー

1. `main`ブランチに Push
2. GitHub Actions が Docker イメージをビルド
3. Artifact Registry にプッシュ
4. Cloud Run にデプロイ
5. Cloud Scheduler が定期実行

---
