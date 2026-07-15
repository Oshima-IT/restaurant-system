# Restaurant Management System

飲食店向けの店舗管理システムです。  
スマートフォンから利用できるPOS機能、勤怠管理、売上管理、受発注管理を一元化し、AI OCRを活用した入力補助機能を搭載しています。

## 📌 概要

小規模飲食店で発生する日々の業務を効率化することを目的としたWebアプリケーションです。

紙で管理されることが多い受発注書・納品書などをスマートフォンで撮影し、OCR技術によってデータ入力を支援します。

## ✨ 主な機能

### 🛒 POS機能
- 商品登録・販売処理
- 売上データ保存
- 販売履歴管理
- スマートフォン対応UI

### 📦 受発注管理
- 発注情報登録
- 受注情報管理
- 紙の注文書・納品書をOCRで読み取り
- 入力作業の効率化

### ⏰ 勤怠管理
- 出勤登録
- 退勤登録
- 勤務時間管理
- データベース保存

### 📊 売上管理
- 売上データ表示
- 売上履歴確認
- 管理者向け情報表示

### 🤖 AI / OCR機能
- 画像から文字情報を抽出
- 受発注書などの入力補助
- OCRによる業務効率化

## 🛠 使用技術

### Backend
- Python
- Flask

### Database
- MySQL

### Frontend
- HTML
- CSS
- JavaScript

### AI / OCR
- PaddleOCR
- OpenCV

### Development Environment
- Ubuntu (WSL)
- VS Code
- Git / GitHub

## 📂 ディレクトリ構成
restaurant-system/
│
├── app.py # Flaskメインアプリケーション
├── config.py # 設定ファイル
├── requirements.txt # Python依存ライブラリ
│
├── models/ # DBモデル
├── routes/ # ルーティング
├── templates/ # HTMLテンプレート
├── static/ # CSS・JavaScript等
│
├── ai/ # AI/OCR関連処理
├── utils/ # 共通処理
│
└── tests/ # テストコード

## ⚙️ 環境構築

### 1. リポジトリを取得

```bash
git clone https://github.com/Oshima-IT/restaurant-system.git

cd restaurant-system
2. 仮想環境作成
python3 -m venv venv
3. 仮想環境を有効化

Ubuntu / WSL:

source venv/bin/activate

Windows:

venv\Scripts\activate
4. ライブラリインストール
pip install -r requirements.txt
5. データベース設定

MySQLを起動し、設定ファイルを環境に合わせて変更してください。

config.py
6. テーブル作成
python create_tables.py

管理者作成：

python create_admin.py
7. 起動
python app.py

アクセス:

http://localhost:5000
🔒 注意事項

以下のファイルはGit管理対象外です。

venv/
.env
アップロード画像
データベースファイル
SSL証明書

環境構築後に各自で設定してください。

🚀 今後の改善予定
OCR精度向上
商品マスタ管理機能強化
売上分析機能追加
権限管理機能追加
クラウド環境へのデプロイ対応
📄 License

This project is for educational and development purposes.


---

追加するとGitHub上で見栄えが良くなるもの：

- トップにシステム画面のスクリーンショット
- 使用例（POS画面 → OCR登録 → 売上表示）
- 開発目的（「小規模飲食店のDX化」など）

特に今回のシステムは研究・実習成果として見せられる内容なので、READMEを少し整えるだけでポートフォリオ感がかなり出ます。
