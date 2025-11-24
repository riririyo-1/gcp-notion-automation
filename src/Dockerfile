
# ベースイメージを指定
FROM python:3.12-slim

# Dockerfileの中での作業ディレクトリを指定
WORKDIR /app

# ホストのファイルをコンテナにコピー
COPY . /app

# requirements.txtに記載されたパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポートを開放（EXPOSE命令は、コンテナが外部に公開するポートを指定するためのもの）（今回は使用しない）
# EXPOSE 80

# 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# コンテナが起動したときに実行されるコマンド
CMD ["python", "main.py"]