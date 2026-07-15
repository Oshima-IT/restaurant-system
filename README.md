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


🚀 今後の改善予定
OCR精度向上
商品マスタ管理機能強化
売上分析機能追加
権限管理機能追加
クラウド環境へのデプロイ対応
📄 License

This project is for educational and development purposes.


---
