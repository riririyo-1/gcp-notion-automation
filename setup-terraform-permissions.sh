#!/bin/bash

# -- GCP Terraform CI/CD 権限設定スクリプト --------------

set -e

# 環境変数の確認
if [ -z "$PROJECT_ID" ]; then
  echo "エラー: PROJECT_ID 環境変数が設定されていません"
  echo "実行例: export PROJECT_ID=your-project-id"
  exit 1
fi

echo "プロジェクトID: $PROJECT_ID"
echo ""

# サービスアカウントのメールアドレス
SA_EMAIL="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "GitHub Actions サービスアカウントに Terraform 実行権限を付与します..."
echo "サービスアカウント: $SA_EMAIL"
echo ""


# -- Cloud Scheduler 管理権限 --------------
echo "1. Cloud Scheduler 管理権限を付与中..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudscheduler.admin"


# -- Secret Manager 管理権限 --------------
echo "2. Secret Manager 管理権限を付与中..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.admin"


# -- Service Account 管理権限 --------------
echo "3. Service Account 管理権限を付与中..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountAdmin"


# -- IAM Policy 管理権限 --------------
echo "4. IAM Policy 管理権限を付与中..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/resourcemanager.projectIamAdmin"


# -- Storage 管理権限 (Terraform State用) --------------
echo "5. Storage 管理権限を付与中..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"


echo ""
echo "✅ 権限設定が完了しました"
echo ""
echo "次のステップ:"
echo "1. GitHub Secrets を設定"
echo "2. terraform/ ディレクトリの変更を commit & push"
echo "3. GitHub Actions が自動実行されることを確認"
