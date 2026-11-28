# video

ブラウザで動くアプリのデモや、プレゼンテーションのスライドを素材に、ナレーションと字幕付きの紹介動画を作る Claude Code の skill です。コンテスト応募用の数分の動画などを想定しています。

skill は手順書で、コードは同梱していません。収録スクリプトや Remotion のプロジェクトは、手順に沿って Claude がその場で書きます。

## 工程

1. 入力をそろえる（提出先の規定、言語、視聴者、字幕あり版・なし版のどちらを書き出すか、VO の作り方、触れてはいけないもの）
2. 台本を書き、yomiyasu で推敲する。画面の操作や機能は実装と照らし合わせる。ユーザーがスライドにない話を足すなどして直し、確定させる
3. 確定した台本から SRT 字幕を作る。キューの時刻は、合成するなら合成した音声の長さから、録音を使うなら録音の発話の区間から決める（録音はこの工程で渡す）
4. 映像素材を作る。アプリは Playwright で台本の時刻どおりに操作して収録し、スライドはページ画像にする（ぺんたのスタイルに作り直すなら、presentation プラグインの slide-create で作り直してから）
5. ナレーションを用意する。[srt-dubbing](https://github.com/plageoj/srt-dubbing)（Edge TTS）で合成するか、工程 3 で渡した録音を使う
6. Remotion で編集し、字幕を焼き込み、VO と BGM の音量をそろえて書き出す
7. 公開前に、透かし・個人情報の映り込み・権利・ライセンスを確かめて報告する
8. ユーザーが台本や SRT を直したら、変わったところだけを作り直して書き出し直す（ナレーションの文言なら、合成は変わったキューの VO を合成し直し、録音はそのキューの録り直しを頼まれる。音声と字幕が同じ言語なら、字幕の直しも読み上げに写す）

音声と字幕の言語は毎回訊かれます（例: 英語音声＋日本語字幕の吹き替え映画風）。

## インストール

台本と作り直したスライドの推敲に、[yomiyasu](https://github.com/nanaism/yomiyasu) プラグインを使います。video プラグインの依存として自動で入りますが、先に yomiyasu のマーケットプレイスを登録しておく必要があります。

```
/plugin marketplace add nanaism/yomiyasu
```

### プラグインとして入れる

```
/plugin marketplace add plageoj/claude-skills
/plugin install video@plageoj
```

### skill だけを入れる

```
git clone https://github.com/plageoj/claude-skills.git
mkdir -p ~/.claude/skills
ln -s "$PWD/claude-skills/plugins/video/skills/intro-video" ~/.claude/skills/intro-video
```

この場合、yomiyasu は自動で入らないので、[yomiyasu の README](https://github.com/nanaism/yomiyasu) に従って別に入れてください。

## 必要なもの

- Node.js（Remotion、Playwright）
- ffmpeg
- アプリを収録する場合: アプリのブラウザ版を動かせる環境
- スライドを使う場合: PDF を画像にするツール（pdftoppm か pymupdf）。Marp なら Chrome、pptx なら LibreOffice
- VO を合成する場合: Python 3.10 以上と uv（[srt-dubbing](https://github.com/plageoj/srt-dubbing)）

Windows、macOS、Linux で動きます。srt-dubbing の README は Windows での入れ方だけを書いていますが、Edge TTS はネット越しの API なので、OS を問わず同じコマンドで合成できます。ffmpeg と uv は次のように入れます。

| OS | ffmpeg | uv |
|---|---|---|
| Windows | `winget install Gyan.FFmpeg` | `winget install astral-sh.uv` |
| macOS | `brew install ffmpeg` | `brew install uv` |
| Linux | `sudo apt install ffmpeg`（Debian / Ubuntu） | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Remotion は個人と小さな会社（3 人まで）は無料で、それ以外は有料のライセンスが要ります。業務委託の人なども人数に入る場合があるので、[規約](https://www.remotion.dev/docs/terms)で確かめてください。

## 使い方

```
自作の Web アプリの紹介動画を作りたい。コンテスト応募用で 3 分以内、英語音声＋日本語字幕。デモは開発サーバーを Playwright で撮って。
```

```
このスライド（slides/talk.pdf）を、ナレーション付きの 2 分の動画にして。
```

```
このスライド（lecture.pdf）をぺんたスタイルで作り直して、10 分の動画にして。日本語音声＋日本語字幕で、台本の確認は挟まず最後まで。
```

## 構成

```
skills/intro-video/
├── SKILL.md                     工程全体と、入力・台本・公開前の確認
└── references/
    ├── source-app.md            Playwright での収録
    ├── source-slides.md         スライドの画像化、並べ方と強調
    ├── audio.md                 VO（srt-dubbing / 録音）と音量
    └── remotion.md              Remotion での編集と書き出し
```
