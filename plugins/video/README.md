# video

ブラウザで動くアプリのデモや、プレゼンテーションのスライドを素材に、ナレーションと字幕付きの紹介動画を作る Claude Code の skill です。コンテスト応募用の数分の動画などを想定しています。

skill は手順書で、コードは同梱していません。収録スクリプトや Remotion のプロジェクトは、手順に沿って Claude がその場で書きます。

## 工程

1. 入力をそろえる（提出先の規定、言語、視聴者、VO の作り方、触れてはいけないもの）
2. 台本を書く。画面の操作や機能は実装と照らし合わせる。ユーザーがスライドにない話を足すなどして直し、確定させる
3. 確定した台本から SRT 字幕を作る。キューの時刻は、合成した音声の長さから決める
4. 映像素材を作る。アプリは Playwright で台本の時刻どおりに操作して収録し、スライドはページ画像にする
5. ナレーションを用意する。[srt-dubbing](https://github.com/plageoj/srt-dubbing)（Edge TTS）で合成するか、録音ファイルを渡す
6. Remotion で編集し、字幕を焼き込み、VO と BGM の音量をそろえて書き出す
7. 公開前に、透かし・個人情報の映り込み・権利・ライセンスを確かめて報告する
8. ユーザーが台本や SRT を直したら、変わったところだけを作り直して書き出し直す（焼き込む字幕の文言なら書き出し直すだけ、ナレーションの文言なら変わったキューの VO を合成し直す）

音声と字幕の言語は毎回訊かれます（例: 英語音声＋日本語字幕の吹き替え映画風）。

## インストール

### プラグインとして入れる

```
/plugin install video --marketplace plageoj/claude-skills
```

### skill だけを入れる

```
git clone https://github.com/plageoj/claude-skills.git
ln -s "$PWD/claude-skills/plugins/video/skills/intro-video" ~/.claude/skills/intro-video
```

## 必要なもの

- Node.js（Remotion、Playwright）
- ffmpeg
- アプリを収録する場合: アプリのブラウザ版を動かせる環境
- スライドを使う場合: PDF を画像にするツール（pdftoppm か pymupdf）。Marp なら Chrome、pptx なら LibreOffice
- VO を合成する場合: Python 3.10 以上と uv（[srt-dubbing](https://github.com/plageoj/srt-dubbing)）

Remotion は個人と従業員 3 人以下の会社は無料で、それ以外は有料のライセンスが要ります。

## 使い方

```
自作の Web アプリの紹介動画を作りたい。コンテスト応募用で 3 分以内、英語音声＋日本語字幕。デモは開発サーバーを Playwright で撮って。
```

```
このスライド（slides/talk.pdf）を、ナレーション付きの 2 分の動画にして。
```

## 構成

```
skills/intro-video/
├── SKILL.md                     工程全体と、入力・台本・公開前の確認
└── references/
    ├── source-app.md            Playwright での収録
    ├── source-slides.md         スライドの画像化と並べ方
    ├── audio.md                 VO（srt-dubbing / 録音）と音量
    └── remotion.md              Remotion での編集と書き出し
```
